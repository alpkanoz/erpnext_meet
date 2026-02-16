# Custom Prosody Plugins Reference

ERPNext Meet uses custom Prosody (XMPP server) plugins to bridge Jitsi and ERPNext. These plugins are located in `jitsi_setup/prosody-plugins-custom/`.

## Plugin Overview

| Plugin | Purpose | Required |
|---|---|---|
| `mod_dynamic_moderation.lua` | JWT-based moderator assignment | Yes |
| `mod_token_affiliation.lua` | Token-based user affiliation | Yes |
| `mod_frozen_nick.lua` | Enforce display name from JWT | Yes |
| `mod_hook_meeting_end.lua` | Webhook notifications to ERPNext | Yes |
| `mod_muc_wait_for_host.lua` | Wait-for-host logic (deprecated) | No |

## mod_dynamic_moderation.lua

Handles moderator privileges based on JWT token claims.

### Behavior

- **Host joins (moderator=true in JWT):** Assigned as room `owner` (moderator). Any temporary owners are demoted to `member`.
- **Authenticated user joins (valid JWT, not host):** Assigned as `member`. If no owner exists in the room, this user is promoted to temporary `owner`.
- **Guest joins (no JWT):** Assigned as `member` (participant).
- **Owner leaves:** If no other owner exists, the next authenticated participant is promoted.

### Key Functions

- `is_real_host(origin)` — Checks JWT for `moderator=true` or `affiliation=owner`
- `force_affiliation(room, jid, affiliation)` — Sets affiliation with a delayed re-apply for reliability

## mod_token_affiliation.lua

Sets user affiliation based on JWT token context. Works alongside `mod_dynamic_moderation`.

### Behavior

- Reads `context.user.affiliation` from JWT payload
- Maps `owner`, `moderator`, `teacher` → room `owner`
- Maps `context.user.moderator = true` → room `owner`
- All other authenticated users → `member`
- Uses cascading set (repeated affiliation application) for reliability

## mod_frozen_nick.lua

Prevents users from changing their display name in meetings.

### Behavior

- Intercepts presence stanzas before they are broadcast
- Replaces any user-set nickname with the `name` from `jitsi_meet_context_user` in the JWT
- Ensures display names in meetings always match ERPNext user profiles

## mod_hook_meeting_end.lua

Sends webhook notifications to ERPNext when meeting rooms are created or destroyed.

### Configuration

Edit the file directly to set your ERPNext URL and webhook token:

```lua
local webhook_url = "https://your-erpnext-domain.com/api/method/erpnext_meet.erpnext_meet.api.handle_jitsi_event"
local secret_token = "YOUR_WEBHOOK_TOKEN_FROM_MEETING_SETTINGS"
```

### Events

| Jitsi Event | Webhook Payload | ERPNext Action |
|---|---|---|
| `muc-room-created` | `{"event": "room_created", "room": "...", "token": "..."}` | Meeting → Active |
| `muc-room-destroyed` | `{"event": "room_destroyed", "room": "...", "token": "..."}` | Meeting → Waiting |

### Filtering

Only rooms with names starting with `meet-` (case-insensitive) trigger webhooks. Other Jitsi rooms (system rooms, breakout rooms, etc.) are ignored.

## mod_muc_wait_for_host.lua (Deprecated)

This plugin was originally used to enforce a "wait for host" policy. It is no longer actively used but kept for backward compatibility. Its functionality has been superseded by `mod_dynamic_moderation.lua`.

## Installation

```bash
cp -r /path/to/erpnext_meet/jitsi_setup/prosody-plugins-custom/* \
      ~/.jitsi-meet-cfg/prosody/prosody-plugins-custom/
```

After installing or updating plugins, restart Prosody:

```bash
docker compose restart prosody
```

## Enabling Plugins

Plugins are enabled via the `XMPP_MUC_MODULES` variable in your Jitsi `.env` file:

```
XMPP_MUC_MODULES=token_verification,token_affiliation,frozen_nick,dynamic_moderation,hook_meeting_end
```

They are also listed in the `modules_enabled` block of `jitsi-meet.cfg.lua` under the `Component "muc.meet.jitsi" "muc"` section.
