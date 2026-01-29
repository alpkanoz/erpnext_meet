# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
import jwt
import time
import uuid

@frappe.whitelist()
def create_room(doctype, docname):
    """
    Creates a new Jitsi room/session for the given document.
    """
    settings = frappe.get_single("Meeting Settings")
    if not settings.enable_integration:
        frappe.throw(_("Meeting integration is disabled."))

    session_id = str(uuid.uuid4())[:8]
    
    session = frappe.get_doc({
        "doctype": "Meeting",
        "session_id": session_id,
        "reference_doctype": doctype,
        "reference_docname": docname,
        "host": frappe.session.user,
        "start_time": frappe.utils.now(),
        "status": "Active"
    })
    
    session.append("participants", {
        "user": frappe.session.user,
        "invitation_status": "Accepted"
    })
    
    session.insert(ignore_permissions=True)
    
    domain = settings.jitsi_domain or "meet.jit.si"
    if doctype and docname:
        room_name = f"Meet-{doctype}-{docname}-{session_id}".replace(" ", "_")
    else:
        room_name = f"Meet-Instant-{session_id}"
    
    if settings.app_id and settings.app_secret:
        token = generate_jitsi_jwt(settings, room_name, frappe.session.user, is_moderator=True)
    
    domain_url = domain
    if not domain_url.startswith("http"):
        domain_url = f"https://{domain_url}"

    join_link = frappe.utils.get_url(f"/api/method/erpnext_meet.erpnext_meet.erpnext_meet.api.join_room?room_name={room_name}")
    
    return {
        "room_name": room_name,
        "session_name": session.name,
        "join_link": join_link
    }

@frappe.whitelist()
def generate_jitsi_jwt(settings, room_name, user_email, is_moderator=False):
    user_avatar = ""
    user_name = "Guest"
    
    if user_email and frappe.db.exists("User", user_email):
        user_doc = frappe.get_doc("User", user_email)
        user_name = user_doc.full_name
        user_avatar = user_doc.user_image or ""
    elif user_email:
         user_name = user_email 
    
    if not user_email:
         import uuid
         user_email = f"guest-{str(uuid.uuid4())[:8]}"
         user_name = "Guest"
         
    if not settings.app_id or not settings.get_password("app_secret"):
        return None

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
        "room": room_name,
        "moderator": is_moderator,
        "affiliation": "owner" if is_moderator else "member",
        "exp": int(time.time() + 7200)
    }
    
    encoded_jwt = jwt.encode(payload, settings.get_password("app_secret"), algorithm="HS256")
    
    if isinstance(encoded_jwt, bytes):
        return encoded_jwt.decode('utf-8')
    return encoded_jwt

@frappe.whitelist(allow_guest=True)
def join_room(room_name):
    if frappe.session.user == "Guest":
        is_guest = True
        user_email = ""
        is_moderator = False
    else:
        is_guest = False

    settings = frappe.get_single("Meeting Settings")
    
    try:
        parts = room_name.rsplit("-", 1)
        if len(parts) >= 2:
            session_id = parts[1].split("?")[0]
            
            meeting = frappe.db.get_value("Meeting", 
                {"session_id": session_id}, 
                ["name", "status", "host"], 
                as_dict=True
            )
            
            if not meeting:
                 frappe.throw(_("Meeting not found"), frappe.DoesNotExistError)

            if not is_guest:
                is_host = (meeting.host == frappe.session.user)
                is_participant = frappe.db.exists("Meeting Participant", {
                    "parent": meeting.name,
                    "user": frappe.session.user
                })
                
                if not is_host and not is_participant:
                     frappe.throw(_("You are not invited to this meeting."), frappe.PermissionError)

                if meeting.status in ["Active", "Waiting"] and is_host:
                    is_moderator = True
                elif meeting.status in ["Active", "Waiting"]:
                     is_moderator = False
                else:
                     frappe.throw(_("Meeting is not active."), frappe.PermissionError)
            else:
                 if meeting.status not in ["Active", "Waiting"]:
                      frappe.throw(_("Meeting is not active."), frappe.PermissionError)

    except frappe.PermissionError as e:
        raise e
    except Exception as e:
        frappe.log_error(f"Join Error: {str(e)}", "Meeting Join Error")
        is_moderator = False 

    token = generate_jitsi_jwt(settings, room_name, frappe.session.user, is_moderator=is_moderator)
    
    domain = settings.jitsi_domain
    if not domain.startswith("http"):
        domain = f"https://{domain}"
        
    url = f"{domain}/{room_name}"
    if token:
        url += f"?jwt={token}"
    
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = url

@frappe.whitelist()
def invite_users(users, room_name, doctype, docname):
    import json
    if isinstance(users, str):
        try:
            users = json.loads(users)
        except:
             users = [users]

    if not isinstance(users, list):
         users = [users] if users else []

    if not users:
        return

    join_url = frappe.utils.get_url(f"/api/method/erpnext_meet.erpnext_meet.erpnext_meet.api.join_room?room_name={room_name}")

    for user in users:
        if user == frappe.session.user:
            continue
            
        frappe.share.add("Meeting", docname, user, read=1, write=0, share=0)

        doc = frappe.new_doc("Notification Log")
        doc.subject = f"Meeting Invite: {doctype} {docname}"
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

@frappe.whitelist()
def end_meeting(room_name, status="Ended"):
    try:
        parts = room_name.rsplit("-", 1)
        if len(parts) < 2:
            return
            
        session_id = parts[1].split("?")[0]
        
        frappe.db.sql("""
            UPDATE `tabMeeting`
            SET status = %s, modified = NOW()
            WHERE session_id = %s
        """, (status, session_id))
        
        frappe.db.commit()
        return True
    except Exception as e:
        frappe.log_error(f"Failed to end meeting: {str(e)}", "Meeting End Error")
        return False

@frappe.whitelist()
def start_meeting(room_name):
    try:
        parts = room_name.rsplit("-", 1)
        if len(parts) < 2:
            return
            
        session_id = parts[1].split("?")[0]
        
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
    data = frappe.form_dict
    settings = frappe.get_single("Meeting Settings")
    
    if not settings.webhook_token:
        frappe.throw(_("Webhook Token is not configured"), frappe.PermissionError)
        
    if data.get("token") != settings.webhook_token:
         frappe.throw(_("Invalid Webhook Token"), frappe.PermissionError)

    event_type = data.get("event")
    room_name = data.get("room")
    
    if event_type == "room_destroyed" and room_name:
        end_meeting(room_name, status="Waiting")
        return {"status": "success", "message": f"Meeting ended for room {room_name}"}
    
    if event_type == "room_created" and room_name:
        start_meeting(room_name)
        return {"status": "success", "message": f"Meeting started for room {room_name}"}
    
    return {"status": "ignored", "message": "Event not handled"}

@frappe.whitelist()
def update_invitation_status(room_name, status):
    if status not in ["Accepted", "Rejected"]:
         frappe.throw(_("Invalid status"))

    try:
        parts = room_name.rsplit("-", 1)
        if len(parts) < 2:
            return
        session_id = parts[1].split("?")[0]
        
        meeting = frappe.get_doc("Meeting", {"session_id": session_id})
        
        found = False
        for p in meeting.participants:
            if p.user == frappe.session.user:
                p.invitation_status = status
                found = True
                break
        
        if found:
            meeting.save(ignore_permissions=True, update_modified=False)
            return True
        else:
            frappe.throw(_("You are not a participant in this meeting."))

    except Exception as e:
        frappe.log_error(f"RSVP Error: {str(e)}")
        return False
