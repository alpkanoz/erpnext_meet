# ERPNext Meet

**Jitsi Meet video conferencing integration for ERPNext**

ERPNext Meet brings video conferencing directly into your ERPNext instance. Schedule, manage, and join meetings without leaving your ERP system — powered by self-hosted Jitsi Meet and JWT authentication.

## Features

- **Contextual Meetings** — Start video calls directly from ERPNext documents (Tasks, CRM Leads, etc.)
- **JWT Authentication** — Only authenticated ERPNext users can join meetings
- **Dynamic Moderation** — Automatic moderator assignment based on meeting host
- **State Synchronization** — Meeting status updates automatically via webhooks (Active/Waiting/Ended)
- **Integrated Invitations** — Send invitations using ERPNext's built-in notification system
- **Repeating Meetings** — Schedule recurring meetings synced with ERPNext calendar
- **Self-Hosted** — Full control over your data, no third-party dependencies

## Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/alpkanoz/erpnext_meet --branch main
bench install-app erpnext_meet
```

### Requirements

- ERPNext v15
- Python 3.10+
- A self-hosted Jitsi Meet instance ([setup guide](docs/jitsi-setup.md))

## Setup

1. **Set up Jitsi server** → [Jitsi Setup Guide](docs/jitsi-setup.md)
2. **Configure ERPNext** → [Configuration Guide](docs/configuration.md)
3. **Understand the plugins** → [Prosody Plugins Reference](docs/prosody-plugins.md)
4. **Having issues?** → [Troubleshooting](docs/troubleshooting.md)

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to get started.

## License

MIT
