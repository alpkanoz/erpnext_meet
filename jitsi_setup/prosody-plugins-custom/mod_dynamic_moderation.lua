local st = require "util.stanza";
local timer = require "util.timer";
local module = module;

module:log("info", "LOADED mod_dynamic_moderation (v5 - Delayed Enforcement)");

-- Helper to check if user is Real Host based on Token
local function is_real_host(origin)
    local token = origin and origin.auth_token;
    
    if not token then return false; end
    
    local context_user = token.context and token.context.user;
    
    -- Check deeply nested context
    if context_user then
        if context_user.moderator == true or context_user.moderator == "true" then return true; end
        if context_user.affiliation == "owner" then return true; end
    end
    
    -- Check top-level claims
    if token.moderator == true or token.moderator == "true" then return true; end
    if token.affiliation == "owner" then return true; end
    
    return false;
end

-- Helper to check if user has ANY valid token (Authenticated)
local function is_authenticated(origin)
    local token = origin and origin.auth_token;
    return token ~= nil;
end

-- Helper to set affiliation repeatedly (to fight other plugins)
local function force_affiliation(room, jid, affiliation)
    module:log("info", "FORCE setting %s to %s", jid, affiliation);
    room:set_affiliation(true, jid, affiliation);
    
    -- Repeat once more after 1s just to be sure
    timer.add_task(1, function()
        room:set_affiliation(true, jid, affiliation);
    end);
end

module:hook("muc-occupant-joined", function(event)
    local room = event.room;
    local occupant = event.occupant;
    local origin = event.origin;

    -- WAIT 3 SECONDS
    -- This allows `mod_token_affiliation` to finish its aggressive 2s loop
    timer.add_task(3, function()
        -- Re-fetch occupant in case they left
        local current_occupant = room:get_occupant_by_nick(occupant.nick);
        if not current_occupant then return; end
        
        local real_host = is_real_host(origin);
        local authenticated = is_authenticated(origin);
        
        module:log("info", "Checking User: %s | Auth: %s | RealHost: %s", current_occupant.jid, tostring(authenticated), tostring(real_host));

        if real_host then
            module:log("info", "=> ACTION: Real Host. Enforcing OWNER.");
            force_affiliation(room, current_occupant.bare_jid, "owner");

            -- Demote others
            for _, other in room:each_occupant() do
                if other.bare_jid ~= current_occupant.bare_jid and other.affiliation == "owner" then
                    module:log("info", "=> ACTION: Demoting previous owner: %s", other.jid);
                    force_affiliation(room, other.bare_jid, "member");
                end
            end
        else
            -- Not Real Host (Guest or Ordinary Member)
            
            -- Check if room has an owner
            local has_owner = false;
            for _, existing in room:each_occupant() do
                if existing.affiliation == "owner" then
                    has_owner = true;
                    break;
                end
            end
            
            if not has_owner then
                -- Room is empty of owners
                if authenticated then
                    module:log("info", "=> ACTION: No owner. Promoting Authenticated User to Temp Owner: %s", current_occupant.jid);
                    force_affiliation(room, current_occupant.bare_jid, "owner");
                else
                    module:log("info", "=> ACTION: No owner. User is GUEST. Keeping as Member: %s", current_occupant.jid);
                    -- Explicitly force member to verify
                    force_affiliation(room, current_occupant.bare_jid, "member");
                end
            else
                 -- Room has owner. Ensure this non-host is Member
                 if current_occupant.affiliation == "owner" then
                     module:log("warn", "=> ACTION: Non-host user ended up as Owner! Demoting: %s", current_occupant.jid);
                     force_affiliation(room, current_occupant.bare_jid, "member");
                 end
            end
        end
    end);
end);

-- Hook: Occupant Left logic remains similar but simpler
module:hook("muc-occupant-left", function(event)
    local room = event.room;
    local occupant = event.occupant;
    
    if occupant.affiliation ~= "owner" then return; end

    module:log("info", "Owner leaving: %s. Looking for replacement...", occupant.jid);
    
    -- Wait a bit for list to settle
    timer.add_task(1, function()
        local remaining_owner_exists = false;
        local potential_new_owner = nil;

        for _, other in room:each_occupant() do
             if other.affiliation == "owner" then remaining_owner_exists = true; end
             -- Pick first available candidate (Authenticated preferred if we could check, but we can't easily check origin here)
             if not potential_new_owner then potential_new_owner = other; end
        end

        if not remaining_owner_exists and potential_new_owner then
            module:log("info", "Promoting replacement owner: %s", potential_new_owner.jid);
            force_affiliation(room, potential_new_owner.bare_jid, "owner");
        end
    end);
end);
