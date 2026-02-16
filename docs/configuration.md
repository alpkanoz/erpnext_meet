# ERPNext Configuration

After setting up your Jitsi instance, configure the ERPNext side to complete the integration.

## Meeting Settings

Navigate to **Meeting Settings** in your ERPNext instance.

| Field | Description | Example |
|---|---|---|
| Enable Chat | Enable in-meeting chat | Checked |
| Jitsi Domain | Your Jitsi public URL (without `https://`) | `meet.example.com:8443` |
| App ID | Must match `JWT_APP_ID` in Jitsi `.env` | `erpnext_pta` |
| App Secret | Must match `JWT_APP_SECRET` in Jitsi `.env` | Your secret value |
| Webhook Token | Token for Jitsi-to-ERPNext communication | Generate a strong random string |

> **Important:** The `App ID` and `App Secret` values must be identical on both the Jitsi server (`.env` and `jitsi-meet.cfg.lua`) and ERPNext (Meeting Settings).

## How JWT Authentication Works

1. When a user clicks "Join Meeting" in ERPNext, the system generates a JWT token containing:
   - User identity (email, full name)
   - Room name
   - Moderator status (host vs. participant)
2. The token is signed with `App Secret` and sent to Jitsi.
3. Jitsi's Prosody server validates the token using the same `App Secret`.
4. Custom plugins handle moderator assignment and nickname enforcement.

## Webhook Communication

The webhook enables Jitsi to notify ERPNext about meeting events:

- **Room Created** → Meeting status changes to "Active"
- **Room Destroyed** → Meeting status changes to "Waiting" (with 1-hour timeout before "Ended")

The webhook URL is configured in the `mod_hook_meeting_end.lua` plugin on the Jitsi server side.

## Meeting Lifecycle

| Status | Description |
|---|---|
| Open | Meeting created, not yet started |
| Active | At least one participant is in the room |
| Waiting | All participants left, waiting for rejoin (1-hour timeout) |
| Ended | Meeting concluded (manual or auto-timeout) |

### Automatic Timeout Rules

- **Waiting → Ended:** 1 hour after last participant leaves (non-repeating meetings)
- **Active → Ended:** 24 hours of inactivity with no webhook activity (non-repeating meetings)
- **Repeating meetings:** Auto-end after `repeat_till` date. If `repeat_till` is not set, the meeting continues indefinitely.
