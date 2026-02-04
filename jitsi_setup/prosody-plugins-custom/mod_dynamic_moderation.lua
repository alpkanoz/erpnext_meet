local st = require "util.stanza";
local timer = require "util.timer";
local module = module;

module:log("info", "LOADED mod_dynamic_moderation (v8 - Robust Lobby Enforcement)");

-- Helper to check if user is Real Host based on Token
local function is_real_host(origin)
    local token = origin and origin.auth_token;
    
    if not token then return false; end
    
    local context_user = token.context and token.context.user;
    
    if context_user then
        if context_user.moderator == true or context_user.moderator == "true" then return true; end
        if context_user.affiliation == "owner" then return true; end
    end
    
    if token.moderator == true or token.moderator == "true" then return true; end
    if token.affiliation == "owner" then return true; end
    
    return false;
end

local function is_authenticated(origin)
    local token = origin and origin.auth_token;
    return token ~= nil;
end

local function force_affiliation(room, jid, affiliation)
    room:set_affiliation(true, jid, affiliation);
    timer.add_task(1, function()
        room:set_affiliation(true, jid, affiliation);
    end);
end

-- Check if Lobby is enabled, enable it if not
local function check_and_enforce_lobby(room)
    local lobby_enabled = false;
    
    -- Check various ways Prosody stores lobby state
    if room.get_lobby and room:get_lobby() then lobby_enabled = true; end
    if room._data and room._data.lobby then lobby_enabled = true; end
    
    if not lobby_enabled then
        module:log("warn", "Lobby DETECTED DISABLED for %s. Re-enforcing...", room.jid);
        
        if room.set_lobby then room:set_lobby(true); end
        if room._data then room._data.lobby = true; end
        
        -- Also update config map to be sure
        local config = room:get_config();
        if not config then config = {}; end
        config["muc#roomconfig_enable_lobby"] = true;
        config["muc#roomconfig_membersonly"] = true; -- FORCE PRIVATE ROOM
        room:set_config(config);
        
        -- Direct setter if available
        if room.set_members_only then room:set_members_only(true); end
        
        return true; -- We just enabled it
    end
    
    -- Even if lobby was enabled, ensure members_only is true
    if not room:get_members_only() then
        module:log("warn", "Room was Public. Forcing Members-Only for Lobby: %s", room.jid);
        if room.set_members_only then room:set_members_only(true); end
        local config = room:get_config();
        if not config then config = {}; end
        config["muc#roomconfig_membersonly"] = true;
        room:set_config(config);
    end
    
    return false; -- Already enabled
end

module:hook("muc-occupant-joined", function(event)
    local room = event.room;
    local occupant = event.occupant;
    local origin = event.origin;

    timer.add_task(2, function()
        -- Re-fetch occupant
        local current_occupant = room:get_occupant_by_nick(occupant.nick);
        if not current_occupant then return; end
        
        local real_host = is_real_host(origin);
        local authenticated = is_authenticated(origin);
        
        -- ENFORCE LOBBY CHECK
        local just_enabled_lobby = check_and_enforce_lobby(room);
        
        if real_host then
            module:log("info", "User is HOST: %s", current_occupant.jid);
            force_affiliation(room, current_occupant.bare_jid, "owner");
            
            -- Scan room for accidental owners
            for _, other in room:each_occupant() do
                if other.bare_jid ~= current_occupant.bare_jid and other.affiliation == "owner" then
                    module:log("info", "Demoting accidental owner: %s", other.jid);
                    force_affiliation(room, other.bare_jid, "member");
                end
            end
        else
            -- GUEST or Ordinary Member
            -- If we just detected Lobby was OFF, and this user is NOT authenticated,
            -- they likely bypassed the lobby. Force them back to 'none'.
            if not authenticated and just_enabled_lobby then
                 module:log("warn", "User %s bypassed lobby (was disabled). Forcing to Lobby.", current_occupant.jid);
                 force_affiliation(room, current_occupant.bare_jid, "none");
            end
            
            -- Standard logic for empty rooms
            local has_owner = false;
            for _, existing in room:each_occupant() do
                if existing.affiliation == "owner" then has_owner = true; break; end
            end
            
            if not has_owner then
                if authenticated then
                    force_affiliation(room, current_occupant.bare_jid, "owner");
                else
                    module:log("info", "No owner. Forcing Guest %s to Lobby.", current_occupant.jid);
                    force_affiliation(room, current_occupant.bare_jid, "none");
                end
            else
                 -- Room has owner.
                 -- If this user is an accidental 'owner' (e.g. created room race condition), demote.
                 if current_occupant.affiliation == "owner" then
                     module:log("warn", "Non-host user %s has Owner role. Demoting.", current_occupant.jid);
                     -- If they are authenticated, maybe member? If guest, surely none/lobby.
                     if authenticated then
                         force_affiliation(room, current_occupant.bare_jid, "member");
                     else
                         force_affiliation(room, current_occupant.bare_jid, "none");
                     end
                 end
            end
        end
    end);
end);

module:hook("muc-occupant-left", function(event)
    local room = event.room;
    local occupant = event.occupant;
    
    if occupant.affiliation ~= "owner" then return; end

    timer.add_task(1, function()
        local remaining_owner_exists = false;
        local potential_new_owner = nil;

        for _, other in room:each_occupant() do
             if other.affiliation == "owner" then remaining_owner_exists = true; end
             if not potential_new_owner then potential_new_owner = other; end
        end

        if not remaining_owner_exists and potential_new_owner then
            force_affiliation(room, potential_new_owner.bare_jid, "owner");
        end
    end);
end);

-- Hook: Room Created - Force Lobby Mode (Still useful for initial creation)
module:hook("muc-room-created", function(event)
    local room = event.room;
    check_and_enforce_lobby(room);
end);
