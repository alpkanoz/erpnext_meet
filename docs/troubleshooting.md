# Troubleshooting

Common issues and solutions for ERPNext Meet.

## "Waiting for Moderator" or "Asking to Join"

**Cause:** Lobby mode is enabled on the Jitsi server.

**Solution:**
1. Ensure `muc_lobby_rooms` is **NOT** listed in `XMPP_MUC_MODULES` in your `.env` file.
2. Verify that the `modules_enabled` block in `jitsi-meet.cfg.lua` does not include `muc_lobby_rooms`.
3. Restart Prosody:
   ```bash
   docker compose restart prosody
   ```

## JWT Authentication Failed

**Cause:** Mismatch between ERPNext and Jitsi JWT configuration.

**Checklist:**
- `JWT_APP_ID` in `.env` matches **App ID** in ERPNext Meeting Settings
- `JWT_APP_SECRET` in `.env` matches **App Secret** in ERPNext Meeting Settings
- `app_id` and `app_secret` in `jitsi-meet.cfg.lua` match the same values
- `allow_empty_token` is set to `false` in `jitsi-meet.cfg.lua`
- The `pyjwt` Python package is installed in your bench environment

## Webhook Not Working (Meeting Status Not Updating)

**Cause:** The Jitsi server cannot reach ERPNext or the webhook token is wrong.

**Checklist:**
1. Verify `webhook_url` in `mod_hook_meeting_end.lua` points to your correct ERPNext URL:
   ```lua
   local webhook_url = "https://your-erpnext-domain.com/api/method/erpnext_meet.erpnext_meet.api.handle_jitsi_event"
   ```
2. Verify `secret_token` matches **Webhook Token** in ERPNext Meeting Settings.
3. Ensure the Jitsi server can reach your ERPNext URL (check firewall/DNS).
4. Check Prosody logs for errors:
   ```bash
   docker logs docker-jitsi-meet-prosody-1
   ```

## Meeting Stuck in "Active" Status

**Cause:** The webhook for `room_destroyed` was not received by ERPNext.

**Solutions:**
- The hourly scheduled task will automatically close meetings stuck in "Active" for more than 24 hours.
- You can manually set the meeting status to "Ended" from within ERPNext.
- Check the webhook configuration as described above.

## Users Cannot Join Meetings

**Possible causes:**
1. **Jitsi server not reachable:** Verify your `PUBLIC_URL` and firewall settings. Ports 8443 (HTTPS), 10000/udp (JVB media) must be open.
2. **SSL certificate issues:** Check that your SSL certificate is valid or that users accept self-signed certificates.
3. **CORS issues:** Ensure `ENABLE_CORS=1` is set in your Jitsi `.env`.

## Repeating Meetings Ending Prematurely

**Cause:** The `repeat_till` date has passed.

**Note:** If `repeat_till` is not set on a repeating meeting, it will run indefinitely and never auto-end. The auto-end logic only activates when `repeat_till` is explicitly set and the date has passed.
