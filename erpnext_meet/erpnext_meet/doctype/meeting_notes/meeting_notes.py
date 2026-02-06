# Copyright (c) 2026, Alpkan Öztürk and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
import json


class MeetingNotes(Document):
    def before_insert(self):
        if not self.created_at:
            self.created_at = now_datetime()
    
    def get_transcript_text(self):
        """Returns transcript as plain text with timestamps"""
        if not self.raw_transcript:
            return ""
        
        try:
            transcript = json.loads(self.raw_transcript)
            lines = []
            for item in transcript:
                timestamp = f"[{int(item['start']//60):02d}:{int(item['start']%60):02d}]"
                speaker = item.get('speaker', 'Speaker')
                text = item.get('text', '')
                lines.append(f"{timestamp} {speaker}: {text}")
            return "\n".join(lines)
        except (json.JSONDecodeError, KeyError):
            return ""
    
    def get_transcript_for_export(self):
        """Returns structured transcript data for export"""
        if not self.raw_transcript:
            return []
        
        try:
            return json.loads(self.raw_transcript)
        except json.JSONDecodeError:
            return []
