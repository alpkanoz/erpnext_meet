# Jitsi Meet Setup for ERPNext Meet

This directory contains the configuration files and custom Prosody plugins required to integrate Jitsi Meet with ERPNext Meet.

## Prerequisites

- Docker and Docker Compose installed
- ERPNext with `erpnext_meet` app installed
- Domain name or static IP address for Jitsi server

## Quick Setup

### 1. Clone Jitsi Docker Repository

```bash
cd ~
git clone https://github.com/jitsi/docker-jitsi-meet.git jitsi
cd jitsi/docker-jitsi-meet
```

### 2. Configure Environment

```bash
# Copy sample env file
cp env.example .env

# Generate passwords
./gen-passwords.sh

# Edit .env with your settings
nano .env
```

**Required `.env` settings:**

| Variable | Description | Example |
|----------|-------------|---------|
| `PUBLIC_URL` | Your Jitsi public URL | `https://meet.example.com` |
| `JVB_ADVERTISE_IPS` | Your public IP | `1.2.3.4` |
| `ENABLE_AUTH` | Enable authentication | `1` |
| `ENABLE_GUESTS` | Allow guests | `0` |
| `AUTH_TYPE` | Authentication type | `jwt` |
| `JWT_APP_ID` | Must match ERPNext Meeting Settings | `erpnext_pta` |
| `JWT_APP_SECRET` | Must match ERPNext Meeting Settings | `your_secret_here` |
| `XMPP_MUC_MODULES` | Required modules (see below) | - |

**Required XMPP_MUC_MODULES:**
```
XMPP_MUC_MODULES=token_verification,token_affiliation,frozen_nick,dynamic_moderation,hook_meeting_end
```

> ⚠️ **Note:** Do NOT include `muc_lobby_rooms` - it conflicts with JWT authentication.

### 3. Install Custom Prosody Plugins

```bash
# Create config directory if not exists
mkdir -p ~/.jitsi-meet-cfg

# Start Jitsi once to generate default config
docker compose up -d
docker compose down

# Copy custom plugins
cp -r /path/to/erpnext_meet/jitsi_setup/prosody-plugins-custom/* \
      ~/.jitsi-meet-cfg/prosody/prosody-plugins-custom/
```

### 4. Configure Prosody

Replace the generated config with the sample:

```bash
cp /path/to/erpnext_meet/jitsi_setup/jitsi-meet.cfg.lua.example \
   ~/.jitsi-meet-cfg/prosody/config/conf.d/jitsi-meet.cfg.lua
```

**Edit the file and replace placeholders:**
- `YOUR_APP_ID` → Your JWT App ID from Meeting Settings
- `YOUR_APP_SECRET` → Your JWT App Secret from Meeting Settings

### 5. Configure Webhook (mod_hook_meeting_end.lua)

Edit `~/.jitsi-meet-cfg/prosody/prosody-plugins-custom/mod_hook_meeting_end.lua`:

```lua
local webhook_url = "https://your-erpnext-domain.com/api/method/erpnext_meet.erpnext_meet.api.handle_jitsi_event"
local secret_token = "YOUR_WEBHOOK_TOKEN_FROM_MEETING_SETTINGS"
```

### 6. Start Jitsi

```bash
cd ~/jitsi/docker-jitsi-meet
docker compose up -d
```

### 7. Configure ERPNext Meeting Settings

In ERPNext, go to **Meeting Settings** and configure:

| Field | Value |
|-------|-------|
| Enable Chat | ✓ |
| Jitsi Domain | Your Jitsi URL (without https://) |
| App ID | Same as `JWT_APP_ID` in .env |
| App Secret | Same as `JWT_APP_SECRET` in .env |
| Webhook Token | Generate and use in mod_hook_meeting_end.lua |

---

## Files in This Directory

| File | Description |
|------|-------------|
| `env.example` | Sample .env file for Docker Compose |
| `jitsi-meet.cfg.lua.example` | Sample Prosody configuration (no lobby) |
| `prosody-plugins-custom/` | Custom Prosody plugins |

### Custom Plugins

| Plugin | Purpose |
|--------|---------|
| `mod_dynamic_moderation.lua` | JWT-based moderator assignment |
| `mod_token_affiliation.lua` | Token-based user affiliation |
| `mod_frozen_nick.lua` | Prevents nickname changes |
| `mod_hook_meeting_end.lua` | Webhook notifications to ERPNext |
| `mod_muc_wait_for_host.lua` | (Deprecated, kept for compatibility) |

---

## Troubleshooting

### "Waiting for moderator" or "Asking to join"

- Ensure `muc_lobby_rooms` is NOT in `XMPP_MUC_MODULES`
- Verify lobby-related lines are removed from `jitsi-meet.cfg.lua`
- Restart Prosody: `docker compose restart prosody`

### JWT Authentication Failed

- Check `JWT_APP_ID` and `JWT_APP_SECRET` match in both .env and ERPNext
- Verify `app_id` and `app_secret` in `jitsi-meet.cfg.lua`

### Webhook Not Working

- Check `webhook_url` points to correct ERPNext URL
- Verify `secret_token` matches ERPNext Meeting Settings
- Check Prosody logs: `docker logs docker-jitsi-meet-prosody-1`

---

## Updating Configuration

After any config changes:

```bash
cd ~/jitsi/docker-jitsi-meet
docker compose restart prosody
# OR for full restart:
docker compose down && docker compose up -d
```
