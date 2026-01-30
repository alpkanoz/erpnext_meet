### ERPNext Meet

Jitsi video conferencing app integration for Erpnext

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/alpkanoz/erpnext_meet --branch version-15
bench install-app erpnext_meet
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/erpnext_meet
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit

## Production Deployment

This app requires a self-hosted Jitsi instance with specific configurations to enable JWT authentication and dynamic moderation.

### 1. Jitsi Docker Setup

We recommend using the official [Docker setup for Jitsi Meet](https://github.com/jitsi/docker-jitsi-meet).

1.  Clone the repository:
    ```bash
    git clone https://github.com/jitsi/docker-jitsi-meet
    cd docker-jitsi-meet
    ```
2.  Follow their guide to generate passwords (`./gen-passwords.sh`) and create config directories.

### 2. Configuration (`.env`)

You can find a template configuration file in `apps/erpnext_meet/jitsi_setup/env.example`.

Copy the settings from `env.example` to your `.env` file, ensuring you set:
-   `PUBLIC_URL`: Your Jitsi URL (e.g., `https://meet.yourco.com:8443`)
-   `ENABLE_AUTH=1`
-   `AUTH_TYPE=jwt`
-   `JWT_APP_ID`: Must match **App ID** in ERPNext "Meeting Settings" (e.g., `erpnext_pta`).
-   `JWT_APP_SECRET`: Must match **App Secret** in ERPNext "Meeting Settings".
-   `XMPP_MUC_MODULES`: Ensure all `token_verification`, `token_affiliation`, `dynamic_moderation`, `hook_meeting_end` are listed.

### 3. Custom Plugins (Prosody)

This integration relies on custom Prosody plugins for features like:
-   **Dynamic Moderation**: The meeting creator becomes the moderator.
-   **Meeting End Hook**: Notifies ERPNext when a meeting ends (everyone leaves).

**Installation:**
1.  Copy the plugins from this app to your Jitsi config folder:
    ```bash
    cp -r apps/erpnext_meet/jitsi_setup/prosody-plugins-custom/* ~/.jitsi-meet-cfg/prosody/prosody-plugins-custom/
    ```
    *(Adjust `~/.jitsi-meet-cfg` to your actual config path)*

    > **IMPORTANT**: You MUST edit `mod_hook_meeting_end.lua` in your Jitsi config folder to set your actual **ERPNext URL** and **Webhook Token**.

2.  Ensure your `docker-compose.yml` mounts this directory correctly to `/prosody-plugins-custom` inside the prosody container (standard in the official docker setup).

3.  Restart your Jitsi containers:
    ```bash
    docker-compose down && docker-compose up -d
    ```

### 4. ERPNext Configuration

1.  Go to **Meeting Settings**.
2.  **Jitsi Domain**: Enter your `PUBLIC_URL` .
3.  **App ID**: Match `JWT_APP_ID` from your `.env`.
4.  **App Secret**: Match `JWT_APP_SECRET` from your `.env`.

