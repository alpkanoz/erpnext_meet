# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
import frappe.share
from frappe.model.document import Document

class Meeting(Document):
    def validate(self):
        if not self.host:
            self.host = frappe.session.user
            
        if not self.session_id:
            import uuid
            self.session_id = str(uuid.uuid4())[:8]

        if not self.start_time:
            self.start_time = frappe.utils.now()

    def on_update(self):
        self.invite_new_participants()
        self.sync_with_event()

    def sync_with_event(self):
        if not self.start_time:
            return

        import datetime
        starts_on = self.start_time
        ends_on = self.end_time
        
        if not ends_on:
            if isinstance(starts_on, str):
                starts_on = frappe.utils.get_datetime(starts_on)
            ends_on = starts_on + datetime.timedelta(hours=1)

        event_participants = []
        if self.host:
             event_participants.append({"reference_doctype": "User", "reference_docname": self.host})
             
        for p in self.participants:
            if p.invitation_status != "Rejected" and p.user != self.host:
                 event_participants.append({"reference_doctype": "User", "reference_docname": p.user})

        if not self.event_ref:
            event = frappe.new_doc("Event")
            event.subject = f"Video Meeting: {self.reference_docname or 'Meeting'}"
            event.starts_on = starts_on
            event.ends_on = ends_on
            event.event_category = "Meeting" 
            event.event_type = "Private"
            event.status = "Open"
            
            description_content = f"Join link: {frappe.utils.get_url()}/app/meeting/{self.name}"
            if self.meeting_details:
                description_content += f"<br><br>{self.meeting_details}"
            
            event.description = description_content
            event.set("event_participants", event_participants)
            # Sync repeat settings
            event.repeat_this_event = self.repeat_this_meeting or 0
            event.repeat_on = self.repeat_on if self.repeat_this_meeting else ""
            event.repeat_till = self.repeat_till if self.repeat_this_meeting else None
            # Sync weekday fields for Weekly repeat
            if self.repeat_this_meeting and self.repeat_on == "Weekly":
                event.monday = getattr(self, 'monday', 0) or 0
                event.tuesday = getattr(self, 'tuesday', 0) or 0
                event.wednesday = getattr(self, 'wednesday', 0) or 0
                event.thursday = getattr(self, 'thursday', 0) or 0
                event.friday = getattr(self, 'friday', 0) or 0
                event.saturday = getattr(self, 'saturday', 0) or 0
                event.sunday = getattr(self, 'sunday', 0) or 0
            event.insert(ignore_permissions=True)
            
            frappe.db.set_value("Meeting", self.name, "event_ref", event.name)
            self.event_ref = event.name
            
        else:
            try:
                event = frappe.get_doc("Event", self.event_ref)
                event.subject = f"Video Meeting: {self.reference_docname or 'Meeting'}"
                event.starts_on = starts_on
                event.ends_on = ends_on
                
                # Update participants safely
                event.set("event_participants", [])
                event.set("event_participants", event_participants)
                
                event.event_category = "Meeting"
                event.event_type = "Private" # Use Private + Share
                
                description_content = f"Join link: {frappe.utils.get_url()}/app/meeting/{self.name}"
                if self.meeting_details:
                    description_content += f"<br><br>{self.meeting_details}"
                event.description = description_content
                
                # Sync repeat settings
                event.repeat_this_event = self.repeat_this_meeting or 0
                event.repeat_on = self.repeat_on if self.repeat_this_meeting else ""
                event.repeat_till = self.repeat_till if self.repeat_this_meeting else None
                # Sync weekday fields for Weekly repeat
                if self.repeat_this_meeting and self.repeat_on == "Weekly":
                    event.monday = getattr(self, 'monday', 0) or 0
                    event.tuesday = getattr(self, 'tuesday', 0) or 0
                    event.wednesday = getattr(self, 'wednesday', 0) or 0
                    event.thursday = getattr(self, 'thursday', 0) or 0
                    event.friday = getattr(self, 'friday', 0) or 0
                    event.saturday = getattr(self, 'saturday', 0) or 0
                    event.sunday = getattr(self, 'sunday', 0) or 0
                event.save(ignore_permissions=True)
            except frappe.DoesNotExistError:
                self.event_ref = None
                self.sync_with_event()
                return

        # Enqueue background job to sync shares
        # This avoids permission issues and speeds up save
        valid_users = [p.get("reference_docname") for p in event_participants]
        if valid_users:
             frappe.enqueue(
                 "erpnext_meet.erpnext_meet.api.sync_event_shares",
                 event_name=event.name,
                 valid_users=valid_users,
                 queue="short",
                 enqueue_after_commit=True
             )


    def invite_new_participants(self):
        try:
            old_doc = self.get_doc_before_save()
            old_participants = set()
            if old_doc:
                old_participants = {p.user for p in old_doc.participants}
                
            new_participants = {p.user for p in self.participants}
            added_users = list(new_participants - old_participants)
            
            if added_users:
                # Enqueue background job - runs as Administrator
                # IMPORTANT: enqueue_after_commit ensures Meeting is saved first
                frappe.enqueue(
                    "erpnext_meet.erpnext_meet.api.send_meeting_invites",
                    meeting_name=self.name,
                    added_users=added_users,
                    queue="short",
                    enqueue_after_commit=True
                )
        except Exception as e:
            frappe.log_error(title="Meeting Invite Error", message=frappe.get_traceback())
