import frappe
from frappe.utils import add_to_date, now_datetime, getdate, nowdate

def hourly():
    """
    Scheduled task (Hourly) to manage Meeting lifecycle.
    1. Check for meetings in "Waiting" status.
    2. If modified > 1 hour ago, set status to "Ended".
    3. If modified > 24 hours ago (Active), set status to "Ended".
    4. Repeating meetings: auto-end after repeat_till date.
    """
    
    # 1. Timeout for Waiting Meetings (1 Hour) - Only non-repeating
    timeout_threshold = add_to_date(now_datetime(), hours=-1)
    
    meetings_to_end = frappe.db.get_all("Meeting", 
        filters={
            "status": "Waiting",
            "modified": ["<", timeout_threshold],
            "repeat_this_meeting": 0
        },
        fields=["name", "session_id", "event_ref"]
    )
    
    for meeting in meetings_to_end:
        frappe.db.set_value("Meeting", meeting.name, "status", "Ended")
        frappe.db.set_value("Meeting", meeting.name, "end_time", frappe.utils.now())
        # Sync Event status
        if meeting.event_ref:
            frappe.db.set_value("Event", meeting.event_ref, "status", "Completed")
        frappe.db.commit()

    # 2. Timeout for Stuck "Active" Meetings (24 Hours) - Only non-repeating
    # Use start_time instead of modified to avoid premature timeout for future meetings
    active_timeout_threshold = add_to_date(now_datetime(), hours=-24)
    
    stuck_meetings = frappe.db.get_all("Meeting",
        filters={
            "status": "Active",
            "start_time": ["<", active_timeout_threshold],
            "repeat_this_meeting": 0
        },
        fields=["name", "event_ref"]
    )
    
    for meeting in stuck_meetings:
        frappe.db.set_value("Meeting", meeting.name, "status", "Ended")
        frappe.db.set_value("Meeting", meeting.name, "end_time", frappe.utils.now())
        # Sync Event status
        if meeting.event_ref:
            frappe.db.set_value("Event", meeting.event_ref, "status", "Completed")
        frappe.db.commit()

    # 3. Repeating meetings: auto-end after repeat_till date
    today = getdate(nowdate())
    
    repeating_meetings = frappe.db.get_all("Meeting",
        filters={
            "status": ["in", ["Active", "Waiting"]],
            "repeat_this_meeting": 1,
            "repeat_till": ["<", today]
        },
        fields=["name", "event_ref"]
    )
    
    for meeting in repeating_meetings:
        frappe.db.set_value("Meeting", meeting.name, "status", "Ended")
        frappe.db.set_value("Meeting", meeting.name, "end_time", frappe.utils.now())
        # Sync Event status to Completed
        if meeting.event_ref:
            frappe.db.set_value("Event", meeting.event_ref, "status", "Completed")
        frappe.db.commit()

