# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
import jwt
import time
import uuid
import os

@frappe.whitelist()
def create_room(doctype, docname):
    """
    Creates a new Jitsi room/session for the given document.
    Returns: { "room_url": "...", "session_name": "..." }
    """
    settings = frappe.get_single("Meeting Settings")
    if not settings.enable_chat:
        frappe.throw(_("Meeting integration is disabled."))

    # Generate a unique session ID
    session_id = str(uuid.uuid4())[:8]
    
    # Create Call Session Record
    session_data = {
        "doctype": "Meeting",
        "session_id": session_id,
        "reference_doctype": doctype,
        "reference_docname": docname,
        "host": frappe.session.user,
        "start_time": frappe.utils.now(),
        "status": "Active"
    }

    # If linked to an Event, sync recurrence and timing details
    if doctype == "Event" and docname:
        try:
            event_doc = frappe.get_doc("Event", docname)
            session_data["start_time"] = event_doc.starts_on
            session_data["end_time"] = event_doc.ends_on
            session_data["event_ref"] = docname
            
            if event_doc.repeat_this_event:
                session_data["repeat_this_meeting"] = 1
                session_data["repeat_on"] = event_doc.repeat_on
                session_data["repeat_till"] = event_doc.repeat_till
                
                if event_doc.repeat_on == "Weekly":
                    for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                        session_data[day] = event_doc.get(day)
        except Exception as e:
            frappe.log_error(f"Failed to sync Event details to Meeting: {str(e)}", "Meeting Creation Error")

    session = frappe.get_doc(session_data)
    
    # Add host as participant
    session.append("participants", {
        "user": frappe.session.user,
        "invitation_status": "Accepted"
    })
    
    session.insert(ignore_permissions=True)
    
    # Construct Jitsi URL
    domain = settings.jitsi_domain or "meet.jit.si"
    # Room name format: Meet-DocType-DocName-SessionID (Sanitized)
    if doctype and docname:
        room_name = f"Meet-{doctype}-{docname}-{session_id}".replace(" ", "_")
    else:
        room_name = f"Meet-Instant-{session_id}"
    
    token = None
    if settings.app_id and settings.app_secret:
        # Default behavior for room creation: Creator gets moderator rights
        token = generate_jitsi_jwt(settings, room_name, frappe.session.user, is_moderator=True)

    domain_url = domain
    if not domain_url.startswith("http"):
        domain_url = f"https://{domain_url}"

    join_link = frappe.utils.get_url(f"/api/method/erpnext_meet.erpnext_meet.api.join_room?room_name={room_name}")
    
    return {
        "room_name": room_name,
        "session_name": session.name,
        "join_link": join_link
    }

@frappe.whitelist()
def generate_jitsi_jwt(settings, room_name, user_email, is_moderator=False):
    """
    Generates a JWT token for Jitsi Meet (SaaS or Self-hosted with auth).
    Payload heavily depends on Jitsi configuration.
    """
    user_avatar = ""
    user_name = "Guest"
    
    if user_email and frappe.db.exists("User", user_email):
        user_doc = frappe.get_doc("User", user_email)
        user_name = user_doc.full_name
        user_avatar = user_doc.user_image or ""
    elif user_email:
         user_name = user_email # Fallback if email provided but no doc (unlikely for Guests)
    
    # Guest Handling
    if not user_email:
         import uuid
         user_email = f"guest-{str(uuid.uuid4())[:8]}" # Random ID for guest
         user_name = "Guest" # Or let them set it in Jitsi UI if possible, but token usually overrides

    payload = {
        "context": {
            "user": {
                "avatar": user_avatar,
                "name": user_name,
                "email": user_email,
                "id": user_email,
                "moderator": is_moderator,
                "affiliation": "owner" if is_moderator else "member"
            },
            "features": {
                "livestreaming": is_moderator,
                "recording": is_moderator
            }
        },
        "aud": "jitsi",
        "iss": settings.app_id,
        "sub": "meet.jitsi",
        "room": "*", # Using wildcard to avoid regex mismatches
        "moderator": is_moderator,
        "affiliation": "owner" if is_moderator else "member",
        "exp": int(time.time() + 7200) # 2 hours
    }
    
    # Debug logging
    frappe.log_error(f"JWT Payload: {payload}\nSecret Length: {len(settings.get_password('app_secret') or '')}", "Jitsi Token Debug")
    
    encoded_jwt = jwt.encode(payload, settings.get_password("app_secret"), algorithm="HS256")
    
    # DEBUG LOG
    frappe.log_error(title="Jitsi JWT Debug", message=f"User: {user_email}, Is Moderator: {is_moderator}, Payload: {payload}, Token: {encoded_jwt}")
    
    if isinstance(encoded_jwt, bytes):
        return encoded_jwt.decode('utf-8')
    return encoded_jwt

# ... (join_room unchanged)

@frappe.whitelist()
def update_invitation_status(room_name, status):
    logged_user = frappe.session.user
    frappe.log_error(f"RSVP Request: User={logged_user}, Room={room_name}, Status={status}", "RSVP Debug")
    
    if status not in ["Accepted", "Rejected"]:
         frappe.throw(_("Invalid status"))

    try:
        parts = room_name.rsplit("-", 1)
        if len(parts) < 2:
            frappe.log_error(f"Invalid Room Name Format: {room_name}", "RSVP Error")
            return
            
        session_id = parts[1].split("?")[0]
        frappe.log_error(f"Extracted Session ID: {session_id}", "RSVP Debug")
        
        meeting = frappe.get_doc("Meeting", {"session_id": session_id})
        if not meeting:
            frappe.log_error("Meeting not found", "RSVP Error")
            return
            
        found = False
        for p in meeting.participants:
            if p.user == logged_user:
                p.invitation_status = status
                found = True
                break
        
        if found:
            # Try saving without updating modified timestamp to avoid concurrency issues
            meeting.flags.ignore_permissions = True
            meeting.save(ignore_permissions=True)
            frappe.db.commit()
            frappe.log_error("Meeting Saved Successfully", "RSVP Debug")
            return True
        else:
            frappe.log_error(f"User {logged_user} not found in participants: {[p.user for p in meeting.participants]}", "RSVP Error")
            frappe.throw(_("You are not a participant in this meeting."))

    except Exception as e:
        frappe.log_error(f"RSVP Exception: {frappe.get_traceback()}", "RSVP Exception")
        return False

@frappe.whitelist(allow_guest=True)
def join_room(room_name):
    """
    Generates a token for the current user and redirects to the Jitsi room.
    Usage: /api/method/erpnext_meet.erpnext_meet.api.join_room?room_name=...
    """
    if frappe.session.user == "Guest":
        # Guest Access Logic
        is_guest = True
        user_email = "" # No email for guest
        is_moderator = False
        
        # We can implement token validation here if needed, but for now open for invited guests
        # Validating existence of meeting is enough for basic security
        pass
    else:
        is_guest = False

    settings = frappe.get_single("Meeting Settings")
    
    # 1. GET MEETING DETAILS
    # Extract session_id from room_name (Meet-{doc}-{name}-{session_id})
    # OR Meet-Instant-{session_id}
    try:
        parts = room_name.rsplit("-", 1)
        if len(parts) >= 2:
            session_id = parts[1].split("?")[0]
            
            # Fetch Host and Participants
            meeting = frappe.db.get_value("Meeting", 
                {"session_id": session_id}, 
                ["name", "status", "host"], 
                as_dict=True
            )
            
            if not meeting:
                 frappe.throw(_("Meeting not found"), frappe.DoesNotExistError)

            # 2. STRICT PARTICIPANT CHECK (Skip for Guests if desired, or validate token)
            if not is_guest:
                # Allow if User is Host
                is_host = (meeting.host == frappe.session.user)
                
                # Allow if User is in Participants List
                is_participant = frappe.db.exists("Meeting Participant", {
                    "parent": meeting.name,
                    "user": frappe.session.user
                })
                
                # DENY if neither
                if not is_host and not is_participant:
                     frappe.throw(_("You are not invited to this meeting."), frappe.PermissionError)

                # 3. DETERMINE MODERATOR STATUS
                # STRICT CHECK: Only the recorded host can be moderator
                # Allow joining if Active or Waiting
                if meeting.status in ["Active", "Waiting"] and is_host:
                    is_moderator = True
                elif meeting.status in ["Active", "Waiting"]:
                     is_moderator = False
                else:
                     frappe.throw(_("Meeting is not active."), frappe.PermissionError)
            else:
                 # Guest logic for meeting status
                 if meeting.status not in ["Active", "Waiting"]:
                      frappe.throw(_("Meeting is not active."), frappe.PermissionError)

    except frappe.PermissionError as e:
        raise e
    except Exception as e:
        frappe.log_error(f"Join Error: {str(e)}", "Meeting Join Error")
        is_moderator = False 

    token = generate_jitsi_jwt(settings, room_name, frappe.session.user, is_moderator=is_moderator)
    
    # Ensure protocol is present
    domain = settings.jitsi_domain
    if not domain.startswith("http"):
        domain = f"https://{domain}"
        
    url = f"{domain}/{room_name}"
    if token:
        url += f"?jwt={token}"
    
    frappe.log_error(title="Jitsi Join URL", message=f"User: {frappe.session.user}, URL: {url}")
    
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = url

@frappe.whitelist()
def start_instant_meeting():
    """
    Creates a standalone meeting and redirects the user to it.
    Link for Shortcuts: /api/method/erpnext_meet.erpnext_meet.api.start_instant_meeting
    """
    try:
        room_data = create_room(None, None)
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = room_data["join_link"]
    except Exception as e:
        frappe.log_error(f"Instant Meeting Error: {str(e)}")
        frappe.throw(_("Could not start instant meeting. Check logs."))

@frappe.whitelist()
def invite_users(users, room_name, doctype, docname, meeting_name=None):
    """
    API wrapper that enqueues the invite job.
    users: JSON string list of user emails OR list object OR single string
    """
    import json

    # Ensure users is a list
    if hasattr(users, "decode"): # bytes
        users = users.decode("utf-8")
        
    if isinstance(users, str):
        try:
            users = json.loads(users)
        except (ValueError, TypeError):
            if users.startswith("[") and users.endswith("]"):
                 pass 
            else:
                 users = [users]

    if not isinstance(users, list):
         if users:
              users = [users]
         else:
              return

    if not users:
        return

    # Resolve meeting_name from room_name if not provided
    if not meeting_name:
        try:
            parts = room_name.rsplit("-", 1)
            if len(parts) >= 2:
                session_id = parts[1].split("?")[0]
                meeting_name = frappe.db.get_value("Meeting", {"session_id": session_id})
        except Exception:
            pass

    # Enqueue background job - runs as Administrator
    frappe.enqueue(
        "erpnext_meet.erpnext_meet.api.send_meeting_invites",
        meeting_name=meeting_name,
        added_users=users,
        room_name=room_name,
        doctype=doctype,
        docname=docname,
        queue="short"
    )

@frappe.whitelist()
def sync_event_shares(event_name, valid_users):
    """
    Background job to sync Event shares.
    Ensures that only 'valid_users' (and owner) have access.
    Runs as Administrator.
    """
    import frappe.share
    
    # Switch to Administrator
    original_user = frappe.session.user
    frappe.set_user("Administrator")
    
    try:
        if isinstance(valid_users, str):
             import json
             valid_users = json.loads(valid_users)
        
        valid_users_set = set(valid_users)
        
        # 1. Share with valid users
        for user in valid_users:
            if user:
                try:
                    frappe.share.add_docshare("Event", event_name, user, read=1, write=0, share=0, flags={"ignore_share_permission": True, "ignore_permissions": True})
                except Exception as e:
                    frappe.log_error(f"Failed to share Event {event_name} with {user}: {str(e)}", "Event Share Error")

        # 2. Unshare with others (Fetch current shares first)
        try:
             current_shares = frappe.share.get_users("Event", event_name)
             # current_shares is a list of objects with 'user' attribute
             for share in current_shares:
                 if share.user not in valid_users_set and share.user != frappe.db.get_value("Event", event_name, "owner"):
                      try:
                          frappe.share.remove("Event", event_name, share.user, flags={"ignore_share_permission": True, "ignore_permissions": True})
                      except Exception:
                          pass
        except Exception as e:
             frappe.log_error(f"Failed to fetch/remove old shares for {event_name}: {str(e)}", "Event Share Error")

    except Exception as e:
         frappe.log_error(f"Background Sync Share Error: {str(e)}", "Event Share Error")
    finally:
         frappe.set_user(original_user)

def send_meeting_invites(meeting_name, added_users=None, room_name=None, doctype=None, docname=None):
    """
    Background job function to send meeting invitations.
    Runs as Administrator to bypass permission issues.
    """
    if not meeting_name:
        frappe.log_error("send_meeting_invites called without meeting_name", "Meeting Invite Error")
        return
    
    # Switch to Administrator to bypass permission issues
    original_user = frappe.session.user
    frappe.set_user("Administrator")
    
    try:
        meeting = frappe.get_doc("Meeting", meeting_name)
        
        # Determine room_name if not passed
        if not room_name:
            session_id = meeting.session_id
            if meeting.reference_doctype and meeting.reference_docname:
                room_name = f"Meet-{meeting.reference_doctype}-{meeting.reference_docname}-{session_id}".replace(" ", "_")
            else:
                room_name = f"Meet-Instant-{session_id}"
        
        # Determine doctype/docname for notification
        if not doctype:
            doctype = meeting.reference_doctype or "Meeting"
        if not docname:
            docname = meeting.reference_docname or meeting.name
        
        # Build join URL
        join_url = frappe.utils.get_url(f"/api/method/erpnext_meet.erpnext_meet.api.join_room?room_name={room_name}")
        
        # If no specific users provided, use all participants except host
        if not added_users:
            added_users = [p.user for p in meeting.participants if p.user != meeting.host]
        
        for user in added_users:
            if user == meeting.host:
                continue
                
            # Grant Read Permission via Share (running as Admin)
            try:
                frappe.share.add("Meeting", meeting_name, user, read=1, write=0, share=0)
            except Exception as e:
                frappe.log_error(f"Failed to share Meeting {meeting_name} with {user}: {str(e)}", "Meeting Share Error")

            # Create Notification Log
            try:
                doc = frappe.new_doc("Notification Log")
                doc.subject = f"Video Meeting Invite: {doctype} {docname}"
                doc.email_content = f"""
                    <p>You have been invited to a video meeting.</p>
                    <p><b>Reference:</b> {doctype} {docname}</p>
                    <p><a href="{join_url}" target="_blank">Click here to Join Meeting</a></p>
                """
                doc.for_user = user
                doc.document_type = doctype
                doc.document_name = docname
                doc.type = "Alert"
                doc.insert(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Failed to create notification for {user}: {str(e)}", "Meeting Notification Error")

            # Send Email
            try:
                # 1. Host Name
                host_name = frappe.utils.get_fullname(meeting.host)
                intro_msg = _("{0} has invited you to a video meeting.").format(host_name)

                # 2. Repeat Info
                repeat_info = ""
                if meeting.repeat_this_meeting:
                    repeat_info = _(meeting.repeat_on)
                    if meeting.repeat_on == "Weekly":
                        days = []
                        if meeting.monday: days.append(_("Monday"))
                        if meeting.tuesday: days.append(_("Tuesday"))
                        if meeting.wednesday: days.append(_("Wednesday"))
                        if meeting.thursday: days.append(_("Thursday"))
                        if meeting.friday: days.append(_("Friday"))
                        if meeting.saturday: days.append(_("Saturday"))
                        if meeting.sunday: days.append(_("Sunday"))
                        if days:
                            repeat_info += f" ({', '.join(days)})"

                # Prepare Context for Template
                context = {
                    "intro_message": intro_msg,
                    "reference_label": _("Reference"),
                    "reference_doctype": doctype,
                    "reference_docname": docname,
                    "start_time_label": _("Start Time"),
                    "start_time": frappe.utils.format_datetime(meeting.start_time, "medium"),
                    "end_time_label": _("End Time"),
                    "end_time": frappe.utils.format_datetime(meeting.end_time, "medium") if meeting.end_time else None,
                    "details_label": _("Meeting Details"),
                    "meeting_details": meeting.get("meeting_details"),
                    "repeat_label": _("Repeats"),
                    "repeat_info": repeat_info,
                    "join_button_label": _("Click here to Join Meeting"),
                    "join_url": join_url
                }

                # Render Template
                if frappe.db.exists("Email Template", "Meeting Invitation"):
                     template = frappe.get_doc("Email Template", "Meeting Invitation")
                     subject = frappe.render_template(template.subject, context)
                     message = frappe.render_template(template.response, context)
                else:
                     # Fallback if template missing
                     subject = f"Video Meeting Invite: {doctype} {docname}"
                     message = f"""
                        <p>{context['intro_message']}</p>
                        <p><b>{context['reference_label']}:</b> {doctype} {docname}</p>
                        <p><a href="{join_url}" target="_blank">{context['join_button_label']}</a></p>
                     """

                # Format Recipient as "Name <email>"
                recipient_name = frappe.utils.get_fullname(user)
                recipient = f"{recipient_name} <{user}>"

                frappe.sendmail(
                    recipients=[recipient],
                    subject=subject,
                    message=message,
                    reference_doctype="Meeting",
                    reference_name=meeting_name
                )
            except Exception as e:
                frappe.log_error(f"Failed to send meeting invite email to {user}: {str(e)}", "Meeting Email Error")
    finally:
        # Always restore original user
        frappe.set_user(original_user)

@frappe.whitelist()
def get_active_room(doctype, docname):
    """
    Checks if there is an active Meeting Session for this document.
    Returns dict {room_name, host} if active, else None.
    """
    sessions = frappe.get_all("Meeting", 
        filters={
            "reference_doctype": doctype,
            "reference_docname": docname,
            "status": "Active"
        },
        fields=["session_id", "host"],
        order_by="creation desc",
        limit=1
    )
    
    if sessions:
        session = sessions[0]
        # Must match create_room name generation
        room_name = f"Meet-{doctype}-{docname}-{session.session_id}".replace(" ", "_")
        return {
            "room_name": room_name,
            "host": session.host
        }
        
    return None

@frappe.whitelist()
def end_meeting(room_name, status="Ended"):
    """
    Ends the meeting associated with the room_name.
    Extracts session_id from room_name.
    status: 'Ended' (default, for manual end) or 'Waiting' (for timeout logic)
    """
    try:
        # room_name format: Meet-{doctype}-{docname}-{session_id}
        parts = room_name.rsplit("-", 1)
        if len(parts) < 2:
            return
            
        session_id = parts[1].split("?")[0] # Safety split if query params exist
        
        # Check if this is a repeating meeting
        meeting = frappe.db.get_value("Meeting", 
            {"session_id": session_id}, 
            ["name", "repeat_this_meeting", "event_ref"], 
            as_dict=True
        )
        
        if not meeting:
            return False
        
        # Prevent manual ending of repeating meetings
        if meeting.repeat_this_meeting and status == "Ended":
            frappe.throw(_("Repeating meetings cannot be ended manually. They will end automatically after the repeat_till date."))
        
        # Update meeting status
        frappe.db.sql("""
            UPDATE `tabMeeting`
            SET status = %s, modified = NOW(), end_time = NOW()
            WHERE session_id = %s
        """, (status, session_id))
        
        # Sync Event status for non-repeating meetings that are being ended
        if meeting.event_ref and not meeting.repeat_this_meeting and status == "Ended":
            frappe.db.set_value("Event", meeting.event_ref, "status", "Completed")
        
        frappe.db.commit()
        return True
    except Exception as e:
        frappe.log_error(f"Failed to end meeting: {str(e)}", "Meeting End Error")
        return False

@frappe.whitelist()
def start_meeting(room_name):
    """
    Re-activates a meeting (Waiting -> Active).
    """
    try:
        parts = room_name.rsplit("-", 1)
        if len(parts) < 2:
            return
            
        session_id = parts[1].split("?")[0]
        
        # Only update if current status is Waiting
        frappe.db.sql("""
            UPDATE `tabMeeting`
            SET status = 'Active', modified = NOW()
            WHERE session_id = %s AND status = 'Waiting'
        """, (session_id,))
        
        frappe.db.commit()
        return True
    except Exception as e:
        frappe.log_error(f"Failed to start meeting: {str(e)}", "Meeting Start Error")
        return False

@frappe.whitelist(allow_guest=True)
def handle_jitsi_event(**kwargs):
    """
    Handles incoming webhooks from Jitsi Prosody server.
    Expected Payload: { "event": "room_destroyed", "room": "...", "token": "..." }
    """
    data = frappe.form_dict
    
    # 1. Validate Token
    settings = frappe.get_single("Meeting Settings")
    
    if not settings.webhook_token:
        frappe.throw(_("Webhook Token is not configured in Meeting Settings"), frappe.PermissionError)
        
    if data.get("token") != settings.webhook_token:
         frappe.throw(_("Invalid Webhook Token"), frappe.PermissionError)

    # 2. Process Event
    event_type = data.get("event")
    room_name = data.get("room")
    
    if event_type == "room_destroyed" and room_name:
        # room_name format: Meet-{doctype}-{docname}-{session_id}
        # Webhook event means everyone left -> set to Waiting (for timeout)
        end_meeting(room_name, status="Waiting")
        return {"status": "success", "message": f"Meeting ended for room {room_name}"}
    
    if event_type == "room_created" and room_name:
        start_meeting(room_name)
        return {"status": "success", "message": f"Meeting started for room {room_name}"}
    
    return {"status": "ignored", "message": "Event not handled"}

@frappe.whitelist()
def update_invitation_status(room_name, status):
    """
    Updates the invitation status for the current user in the specified meeting.
    status: 'Accepted' or 'Rejected'
    """
    if status not in ["Accepted", "Rejected"]:
         frappe.throw(_("Invalid status"))

    try:
        parts = room_name.rsplit("-", 1)
        if len(parts) < 2:
            return
        session_id = parts[1].split("?")[0]
        
        meeting = frappe.get_doc("Meeting", {"session_id": session_id})
        
        # Find participant row
        found = False
        for p in meeting.participants:
            if p.user == frappe.session.user:
                p.invitation_status = status
                found = True
                break
        
        if found:
            meeting.save(ignore_permissions=True)
            return True
        else:
            frappe.throw(_("You are not a participant in this meeting."))

    except Exception as e:
        frappe.log_error(f"RSVP Error: {str(e)}")
        return False

@frappe.whitelist()
def get_jitsi_domain():
    settings = frappe.get_single("Meeting Settings")
    return settings.jitsi_domain

# ========== TRANSCRIPTION API ==========

@frappe.whitelist()
def start_transcription(meeting_name, audio_file_path):
    """
    Start transcription for a meeting.
    Enqueues a background job for processing.
    
    Args:
        meeting_name: Name of the Meeting document
        audio_file_path: Path to the audio file (on server)
    
    Returns:
        dict with status and meeting_notes_name
    """
    settings = frappe.get_single("Meeting Settings")
    
    if not settings.enable_transcription:
        frappe.throw(_("Transcription is disabled in Meeting Settings"))
    
    if not os.path.exists(audio_file_path):
        frappe.throw(_("Audio file not found: {0}").format(audio_file_path))
    
    # Create preliminary Meeting Notes record
    notes = frappe.new_doc("Meeting Notes")
    notes.meeting = meeting_name
    notes.transcription_status = "Processing"
    notes.insert(ignore_permissions=True)
    frappe.db.commit()
    
    # Enqueue background job
    delete_after = bool(settings.auto_delete_audio)
    
    frappe.enqueue(
        "erpnext_meet.erpnext_meet.utils.transcription.process_transcription",
        audio_file=audio_file_path,
        meeting_name=meeting_name,
        delete_after=delete_after,
        queue="long",
        timeout=3600  # 1 hour timeout for long recordings
    )
    
    return {
        "status": "processing",
        "meeting_notes_name": notes.name,
        "message": _("Transcription started. This may take a few minutes.")
    }

@frappe.whitelist()
def get_transcription_status(meeting_name):
    """
    Get transcription status for a meeting.
    
    Args:
        meeting_name: Name of the Meeting document
    
    Returns:
        dict with status and notes details
    """
    notes = frappe.get_all("Meeting Notes",
        filters={"meeting": meeting_name},
        fields=["name", "transcription_status", "created_at", "duration"],
        order_by="created_at desc",
        limit=1
    )
    
    if not notes:
        return {"status": "none", "message": _("No transcription found for this meeting")}
    
    note = notes[0]
    return {
        "status": note.transcription_status.lower(),
        "meeting_notes_name": note.name,
        "created_at": note.created_at,
        "duration": note.duration
    }

@frappe.whitelist()
def export_meeting_notes(meeting_notes_name, format="txt"):
    """
    Export meeting notes in specified format.
    
    Args:
        meeting_notes_name: Name of the Meeting Notes document
        format: Export format (txt, docx, pdf)
    
    Returns:
        URL to download the file
    """
    import json as json_lib
    from erpnext_meet.erpnext_meet.utils.transcription import (
        export_to_txt, export_to_docx, export_to_pdf
    )
    
    notes = frappe.get_doc("Meeting Notes", meeting_notes_name)
    
    if not notes.raw_transcript:
        frappe.throw(_("No transcript data available"))
    
    transcript = json_lib.loads(notes.raw_transcript)
    meeting = frappe.get_doc("Meeting", notes.meeting)
    title = f"Meeting Transcript - {meeting.name}"
    
    # Generate file content
    if format == "txt":
        content = export_to_txt(transcript, title)
        filename = f"{meeting_notes_name}.txt"
        content_type = "text/plain"
        file_content = content.encode("utf-8")
    elif format == "docx":
        file_content = export_to_docx(transcript, title)
        filename = f"{meeting_notes_name}.docx"
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif format == "pdf":
        file_content = export_to_pdf(transcript, title)
        filename = f"{meeting_notes_name}.pdf"
        content_type = "application/pdf"
    else:
        frappe.throw(_("Invalid format. Use txt, docx, or pdf"))
    
    # Save as File document
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": filename,
        "attached_to_doctype": "Meeting Notes",
        "attached_to_name": meeting_notes_name,
        "content": file_content,
        "is_private": 1
    })
    file_doc.save(ignore_permissions=True)
    
    return file_doc.file_url

@frappe.whitelist()
def get_audio_storage_path():
    """
    Get the configured audio storage path.
    Creates the directory if it doesn't exist.
    
    Returns:
        Path to audio storage directory
    """
    settings = frappe.get_single("Meeting Settings")
    path = settings.audio_storage_path
    
    # Default: use app directory
    if not path:
        import erpnext_meet
        app_path = os.path.dirname(os.path.dirname(erpnext_meet.__file__))
        path = os.path.join(app_path, "erpnext_meet", "meeting_recordings")
    
    # Create directory if it doesn't exist
    if not os.path.exists(path):
        try:
            os.makedirs(path, exist_ok=True)
        except PermissionError:
            frappe.throw(_("Cannot create audio storage directory: {0}").format(path))
    
    return path

@frappe.whitelist()
def is_transcription_enabled():
    """Check if transcription is enabled in settings."""
    settings = frappe.get_single("Meeting Settings")
    return {
        "enabled": bool(settings.enable_transcription),
        "language": settings.transcription_language or "tr",
        "model": settings.whisper_model or "large-v2"
    }
