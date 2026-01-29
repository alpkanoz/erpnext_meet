import frappe
import json

@frappe.whitelist()
def generate_jitsi_config():
    """
    Generates config.js and interface_config.js content based on Meeting Settings.
    Returns a dict with filenames and content.
    """
    settings = frappe.get_single("Meeting Settings")

    # --- Generate config.js ---
    domain = settings.jitsi_domain or 'meet.jit.si'
    
    # Parse toolbar buttons
    toolbar_buttons = [b.strip() for b in (settings.toolbar_buttons or "").split(',') if b.strip()]
    if not toolbar_buttons:
        # Default buttons if empty
        toolbar_buttons = [
            'microphone', 'camera', 'closedcaptions', 'desktop', 'fullscreen',
            'fodeviceselection', 'hangup', 'profile', 'chat', 'recording',
            'livestreaming', 'etherpad', 'sharedvideo', 'settings', 'raisehand',
            'videoquality', 'filmstrip', 'invite', 'feedback', 'stats', 'shortcuts',
            'tileview', 'videobackgroundblur', 'download', 'help', 'mute-everyone',
            'security'
        ]

    config_js = f"""
var config = {{}};

config.hosts = {{
    domain: '{domain}',
    muc: 'muc.{domain}'
}};

config.bosh = 'https://{domain}/http-bind';
config.websocket = 'wss://{domain}/xmpp-websocket';

config.clientNode = 'http://jitsi.org/jitsimeet';

config.testing = {{
    enableCodecSelectionAPI: true,
    capScreenshareBitrate: 1,
    p2pTestMode: false
}};

config.flags = {{
    sourceNameSignaling: true,
    sendMultipleVideoStreams: true,
    receiveMultipleVideoStreams: true
}};

config.channelLastN = -1;
config.startAudioMuted = {10 if settings.start_audio_muted else "null"};
config.startVideoMuted = {10 if settings.start_video_muted else "null"};
config.startWithAudioMuted = {'true' if settings.start_audio_muted else 'false'};
config.startWithVideoMuted = {'true' if settings.start_video_muted else 'false'};

config.requireDisplayName = {'true' if settings.require_display_name else 'false'};
config.prejoinPageEnabled = {'true' if settings.prejoin_page_enabled else 'false'};

config.disableDeepLinking = false;
config.p2p = {{
    enabled: true,
    useStunTurn: true,
    stunServers: [
        {{ urls: 'stun:meet-jit-si-turnrelay.jitsi.net:443' }}
    ]
}};

config.resolution = {settings.resolution or 720};

config.toolbarButtons = {json.dumps(toolbar_buttons)};

config.analytics = {{}};

config.deploymentInfo = {{}};
    """

    # --- Generate interface_config.js ---
    app_name = settings.app_name or "Jitsi Meet"
    brand_watermark = 'true' if settings.show_brand_watermark else 'false'
    jitsi_watermark = 'true' if settings.show_jitsi_watermark else 'false'
    watermark_link = settings.brand_watermark_link or ""
    bg_color = settings.default_background or "#040404"

    interface_config_js = f"""
var interfaceConfig = {{
    APP_NAME: '{app_name}',
    DEFAULT_BACKGROUND: '{bg_color}',
    SHOW_JITSI_WATERMARK: {jitsi_watermark},
    SHOW_BRAND_WATERMARK: {brand_watermark},
    BRAND_WATERMARK_LINK: '{watermark_link}',
    
    // Default toolbar buttons (legacy fallback)
    TOOLBAR_BUTTONS: {json.dumps(toolbar_buttons)},

    SETTINGS_SECTIONS: [ 'devices', 'language', 'moderator', 'profile', 'calendar', 'sounds', 'more' ],
    
    // Mobile App Promo
    MOBILE_APP_PROMO: true,
    
    // Legacy options
    FILM_STRIP_MAX_HEIGHT: 120,
    VERTICAL_FILMSTRIP: true,
    VIDEO_LAYOUT_FIT: 'both',
    
    // Disable features
    DISABLE_JOIN_LEAVE_NOTIFICATIONS: false,
    DISABLE_VIDEO_BACKGROUND: false,
}};
    """

    return {
        "config.js": config_js,
        "interface_config.js": interface_config_js
    }
