local http = require "net.http"
local json = require "util.json"

module:log("info", "Loading mod_hook_meeting_end (Events/Webhooks)...")

-- Configuration
local webhook_url = "http://your-erpnext-domain.com/api/method/erpnext_meet.erpnext_meet.api.handle_jitsi_event"
local secret_token = "REPLACE_WITH_SECRET_FROM_MEETING_SETTINGS" -- Ensure this matches ERPNext Settings

local function send_webhook(event_type, room)
    local room_name = room.jid:match("^(.*)@.*")
    
    module:log("info", "Event %s detected for: %s", event_type, room_name)

    -- Only trigger for ERPNext Meet rooms (starting with Meet-)
    -- Note: Jitsi/Prosody room names might be case-sensitive or lowercased depending on client
    if not room_name:lower():find("^meet%-") then 
        module:log("debug", "Ignoring non-Meet room: %s", room_name)
        return 
    end

    local payload = json.encode({
        event = event_type,
        room = room_name,
        token = secret_token
    })

    module:log("info", "Sending webhook for room %s event %s to %s", room_name, event_type, webhook_url)

    http.request(webhook_url, {
        method = "POST",
        body = payload,
        headers = { ["Content-Type"] = "application/json" }
    }, function(response_body, response_code)
        module:log("info", "Webhook sent for room %s (%s): Code %s. Response: %s", room_name, event_type, response_code, response_body)
    end)
end

-- Hook: Room Destroyed (Meeting Ended / Waiting)
module:hook("muc-room-destroyed", function(event)
    send_webhook("room_destroyed", event.room)
end)

-- Hook: Room Created (Meeting Started / Resumed)
module:hook("muc-room-created", function(event)
    send_webhook("room_created", event.room)
end)

module:log("info", "mod_hook_meeting_end loaded successfully (Webhook Logic Restored).")
