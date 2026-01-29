import frappe
from frappe.utils import add_to_date, now_datetime

def hourly():
    """
    Scheduled task (Hourly) to manage Meeting lifecycle.
    1. Check for meetings in "Waiting" status.
    2. If modified > 1 hour ago, set status to "Ended".
    3. If modified > 24 hours ago (Active), set status to "Ended".
    """
    
    # 1. Timeout for Waiting Meetings (1 Hour)
    timeout_threshold = add_to_date(now_datetime(), hours=-1)
    
    meetings_to_end = frappe.db.get_all("Meeting", 
        filters={
            "status": "Waiting",
            "modified": ["<", timeout_threshold]
        },
        fields=["name", "session_id"]
    )
    
    for meeting in meetings_to_end:
        frappe.db.set_value("Meeting", meeting.name, "status", "Ended")
        frappe.db.set_value("Meeting", meeting.name, "end_time", frappe.utils.now())
        frappe.db.commit()

    # 2. Timeout for Stuck "Active" Meetings (24 Hours)
    active_timeout_threshold = add_to_date(now_datetime(), hours=-24)
    
    stuck_meetings = frappe.db.get_all("Meeting",
        filters={
            "status": "Active",
            "modified": ["<", active_timeout_threshold]
        },
        fields=["name"]
    )
    
    for meeting in stuck_meetings:
        frappe.db.set_value("Meeting", meeting.name, "status", "Ended")
        frappe.db.set_value("Meeting", meeting.name, "end_time", frappe.utils.now())
        frappe.db.commit()
