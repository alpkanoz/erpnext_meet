local st = require "util.stanza";
local timer = require "util.timer";
local module = module;
module:log("info", "LOADED mod_dynamic_moderation (v13 - NO LOBBY)");

local util = module:require 'util';
local is_admin = util.is_admin;

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

module:hook("muc-occupant-joined", function(event)
    local room = event.room;
    local occupant = event.occupant;
    local origin = event.origin;
    
    timer.add_task(2, function()
        local current_occupant = room:get_occupant_by_nick(occupant.nick);
        if not current_occupant then return; end
        
        -- Skip admin/system users (Jicofo, JVB, etc.)
        if is_admin(current_occupant.bare_jid) then
            module:log("info", "Skipping admin user: %s", current_occupant.jid);
            return;
        end
        
        local real_host = is_real_host(origin);
        local authenticated = is_authenticated(origin);
        
        if real_host then
            -- Real host (moderator in JWT) gets owner
            module:log("info", "User is HOST (owner): %s", current_occupant.jid);
            force_affiliation(room, current_occupant.bare_jid, "owner");
            
            -- Demote any other non-admin owners
            for _, other in room:each_occupant() do
                if other.bare_jid ~= current_occupant.bare_jid 
                   and other.affiliation == "owner" 
                   and not is_admin(other.bare_jid) then
                    module:log("info", "Demoting accidental owner: %s", other.jid);
                    force_affiliation(room, other.bare_jid, "member");
                end
            end
        elseif authenticated then
            -- JWT authenticated non-host user gets member
            module:log("info", "JWT User (member): %s", current_occupant.jid);
            force_affiliation(room, current_occupant.bare_jid, "member");
            
            -- If no owner exists, promote this user
            local has_owner = false;
            for _, existing in room:each_occupant() do
                if existing.affiliation == "owner" and not is_admin(existing.bare_jid) then 
                    has_owner = true; 
                    break; 
                end
            end
            
            if not has_owner then
                module:log("info", "No owner exists. Promoting JWT user %s to owner.", current_occupant.jid);
                force_affiliation(room, current_occupant.bare_jid, "owner");
            end
        else
            -- Guest without JWT - still allow but as participant
            module:log("info", "Guest user (participant): %s", current_occupant.jid);
            force_affiliation(room, current_occupant.bare_jid, "member");
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
            if is_admin(other.bare_jid) then
                -- skip
            elseif other.affiliation == "owner" then 
                remaining_owner_exists = true; 
            elseif not potential_new_owner then 
                potential_new_owner = other; 
            end
        end
        if not remaining_owner_exists and potential_new_owner then
            force_affiliation(room, potential_new_owner.bare_jid, "owner");
        end
    end);
end);
