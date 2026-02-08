# Copyright (c) 2026, Alpkan Öztürk and contributors
# For license information, please see license.txt

import os
import sys
import time
import signal
import asyncio
import logging
from datetime import datetime

# Initialize Frappe if running as script
if __name__ == "__main__":
    import frappe
    if len(sys.argv) < 4:
        print("Usage: python3 -m ... <site> <meeting_name> <output_filename>")
        sys.exit(1)
    
    site = sys.argv[1]
    meeting_name = sys.argv[2]
    output_filename = sys.argv[3]
    
    # Change to sites directory so frappe can find the site
    sites_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "sites"))
    os.chdir(sites_path)
    
    frappe.init(site=site)
    frappe.connect()

import slixmpp
from slixmpp.xmlstream import ET
from erpnext_meet.erpnext_meet.api import generate_jitsi_jwt, get_audio_storage_path

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("JitsiSpeakerLogger")
logger.setLevel(logging.INFO)

class JitsiSpeakerLogger(slixmpp.ClientXMPP):
    def __init__(self, jid, password, room, muc_domain, meeting_name, output_filename, settings):
        slixmpp.ClientXMPP.__init__(self, jid, password)

        self.room = room
        self.muc_domain = muc_domain
        self.meeting_name = meeting_name
        self.output_filename = output_filename
        self.settings = settings
        
        # MUC JID: room@conference.domain
        self.room_jid = f"{self.room}@{self.muc_domain}"
        
        # Mapping: ResourceID -> {"name": "Display Name", "email": "..."}
        self.participants = {}
        
        # Event log file
        self.log_file = self._get_log_file_path()
        
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("groupchat_message", self.on_groupchat_message)
        self.add_event_handler("muc::%s::presence" % self.room_jid, self.on_presence)
        
        # Register extension for dominant speaker
        self.register_plugin('xep_0045') # MUC
        
        # Custom handler for dominant speaker updates (often in message or presence)
        self.add_event_handler("message", self.on_message_custom)

    def _get_log_file_path(self):
        storage_path = get_audio_storage_path()
        # If output_filename has extension, use it, else add .events
        filename = self.output_filename
        if not filename.endswith(".events"):
            filename += ".events"
        return os.path.join(storage_path, filename)

    def _log_event(self, event_type, speaker_id, speaker_name):
        timestamp = time.time()
        line = f"{timestamp}|{event_type}|{speaker_id}|{speaker_name}\n"
        with open(self.log_file, "a") as f:
            f.write(line)
        # Also print to stdout for debug
        print(f"[LOG] {line.strip()}")

    async def start(self, event):
        self.send_presence()
        await self.get_roster()
        
        # Join MUC
        self.plugin['xep_0045'].join_muc(self.room_jid, self.nick)

    def on_presence(self, presence):
        """Handle presence updates to track participants."""
        from_jid = presence['from']
        resource = from_jid.resource
        
        # Extract Nickname
        # Jitsi sends nick in <nick xmlns='http://jabber.org/protocol/nick'>Name</nick>
        # or in <jitsi_participant_display_name>...
        
        nick = ""
        # Try standard nick
        xml = presence.xml
        nick_elem = xml.find("{http://jabber.org/protocol/nick}nick")
        if nick_elem is not None:
            nick = nick_elem.text
            
        if resource and nick:
            self.participants[resource] = nick
            # Log join if needed, but we focus on speaking

    def on_message_custom(self, msg):
        """Handle custom Jitsi events in messages."""
        # Check for dominant-speaker extension
        # <dominant-speaker xmlns='http://jitsi.org/jitmeet/audio' speaker='endpoint_id'/>
        
        xml = msg.xml
        ds_elem = xml.find("{http://jitsi.org/jitmeet/audio}dominant-speaker")
        
        if ds_elem is not None:
            speaker_id = ds_elem.get('speaker')
            speaker_name = self.participants.get(speaker_id, "Unknown")
            self._log_event("DOMINANT_SPEAKER", speaker_id, speaker_name)

    def on_groupchat_message(self, msg):
        pass

def start_logger():
    # 1. Get Settings
    settings = frappe.get_single("Meeting Settings")
    if not settings.enable_speaker_detection:
        print("Speaker detection disabled.")
        return

    meeting = frappe.get_doc("Meeting", meeting_name)
    
    # 2. Config
    xmpp_server = settings.xmpp_server or "127.0.0.1"
    xmpp_port = settings.xmpp_port or 5222
    xmpp_domain = settings.xmpp_domain or "auth.meet.jitsi" # Auth domain is different often
    muc_domain = settings.muc_domain or "conference.meet.jitsi"
    
    room_name = meeting.session_id # Or however the room is named.
    # Usually erpnext_meet creates rooms like "Meeting-SESSIONID"
    # Let's check api.create_room logic. It generates URL .../Meeting-SESSIONID
    # So the room name in Jitsi is "Meeting-{session_id}" (case sensitive usually)
    
    full_room_name = f"Meeting-{meeting.session_id}"
    
    # 3. Auth
    # Use hidden recorder/moderator token
    token = generate_jitsi_jwt(
        settings, 
        full_room_name, 
        user_email="logger@erpnext", 
        is_moderator=True # Needs to be moderator to see hidden info sometimes?
    )
    
    # JID: logger@auth.domain (if using JWT, usually we authorize against auth domain)
    jid = f"logger@{xmpp_domain}"
    
    print(f"Connecting to {xmpp_server}:{xmpp_port} as {jid} for room {full_room_name}...")
    
    # 4. Run
    # Slixmpp requires password to be the token for SASL PLAIN
    xmpp = JitsiSpeakerLogger(jid, token, full_room_name, muc_domain, meeting_name, output_filename, settings)
    
    # Force SASL PLAIN if token used
    xmpp.use_mechanisms = ["PLAIN"]
    
    # Connect
    xmpp.connect(host=xmpp_server, port=xmpp_port)
    xmpp.process(forever=True)

if __name__ == "__main__":
    try:
        start_logger()
    except KeyboardInterrupt:
        print("Interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
