# Jitsi Meet Setup Guide

This guide walks you through setting up a self-hosted Jitsi Meet instance for use with ERPNext Meet.

## Prerequisites

- Docker and Docker Compose installed on your server
- ERPNext instance with `erpnext_meet` app installed
- A domain name or static IP address for your Jitsi server
- SSL certificate (Let's Encrypt or self-signed for testing)

## 1. Clone Jitsi Docker Repository

```bash
cd ~
git clone https://github.com/jitsi/docker-jitsi-meet.git jitsi
cd jitsi
```

## 2. Generate Passwords

```bash
cp env.example .env
./gen-passwords.sh
```

## 3. Configure Environment

Copy the settings from `jitsi_setup/env.example` in the ERPNext Meet app to your `.env` file:

```bash
nano .env
```

### Required Settings

| Variable | Description | Example |
|---|---|---|
| `PUBLIC_URL` | Your Jitsi public URL (include port if non-standard) | `https://meet.example.com:8443` |
| `JVB_ADVERTISE_IPS` | Your server's public IP | `1.2.3.4` |
| `ENABLE_AUTH` | Enable JWT authentication | `1` |
| `ENABLE_GUESTS` | Allow guest users | `1` |
| `AUTH_TYPE` | Authentication type | `jwt` |
| `JWT_APP_ID` | Must match ERPNext Meeting Settings | `erpnext_pta` |
| `JWT_APP_SECRET` | Must match ERPNext Meeting Settings | `your_secret_here` |
| `XMPP_MUC_MODULES` | Required custom modules | See below |

### Required XMPP Modules

```
XMPP_MUC_MODULES=token_verification,token_affiliation,frozen_nick,dynamic_moderation,hook_meeting_end
```

> **Note:** Do NOT include `muc_lobby_rooms` — it conflicts with JWT-based authentication.

## 4. Initial Startup (Generate Default Configs)

Start Jitsi once so it generates the default configuration files, then stop it:

```bash
mkdir -p ~/.jitsi-meet-cfg
docker compose up -d
docker compose down
```

## 5. Install Custom Prosody Plugins

Copy the custom plugins from the ERPNext Meet app:

```bash
cp -r /path/to/erpnext_meet/jitsi_setup/prosody-plugins-custom/* \
      ~/.jitsi-meet-cfg/prosody/prosody-plugins-custom/
```

> Replace `/path/to/erpnext_meet` with your actual app path (e.g., `~/frappe-bench/apps/erpnext_meet`).

See [Prosody Plugins Reference](prosody-plugins.md) for details on each plugin.

## 6. Configure Prosody

Replace the generated Prosody config with the provided example:

```bash
cp /path/to/erpnext_meet/jitsi_setup/jitsi-meet.cfg.lua.example \
   ~/.jitsi-meet-cfg/prosody/config/conf.d/jitsi-meet.cfg.lua
```

Edit the file and replace the placeholders:

```lua
app_id = "YOUR_APP_ID"        -- Same as JWT_APP_ID in .env
app_secret = "YOUR_APP_SECRET" -- Same as JWT_APP_SECRET in .env
```

## 7. Configure Webhook Plugin

Edit `~/.jitsi-meet-cfg/prosody/prosody-plugins-custom/mod_hook_meeting_end.lua`:

```lua
local webhook_url = "https://your-erpnext-domain.com/api/method/erpnext_meet.erpnext_meet.api.handle_jitsi_event"
local secret_token = "YOUR_WEBHOOK_TOKEN_FROM_MEETING_SETTINGS"
```

> The `secret_token` must match the **Webhook Token** field in ERPNext Meeting Settings.

## 8. Start Jitsi

```bash
cd ~/jitsi
docker compose up -d
```

## 9. Verify

- Access `https://your-jitsi-domain:8443` in a browser
- You should see the Jitsi interface (you won't be able to create rooms without a JWT)
- Proceed to [ERPNext Configuration](configuration.md) to complete the setup

## Updating Configuration

After any configuration change:

```bash
# Restart only Prosody (for plugin/config changes)
docker compose restart prosody

# Full restart
docker compose down && docker compose up -d
```
