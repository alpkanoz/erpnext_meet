app_name = "erpnext_meet"
app_title = "ERPNext Meet"
app_publisher = "Alpkan Öztürk"
app_description = "Jitsi video conferencing app integration for Erpnext"
app_email = "ozturk.alpkan@gmail.com"
app_license = "mit"

# Apps
# ------------------

# Required Apps
# required_apps = []

# Note: The user will provide a custom repository URL for the forked 'jitsi_meet' app.
# This app is required for full functionality.


# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "erpnext_meet",
# 		"logo": "/assets/erpnext_meet/logo.png",
# 		"title": "ERPNext Meet",
# 		"route": "/erpnext_meet",
# 		"has_permission": "erpnext_meet.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/erpnext_meet/css/erpnext_meet.css"
app_include_js = "/assets/erpnext_meet/js/meeting.js"

# include js, css files in header of web template
# web_include_css = "/assets/erpnext_meet/css/erpnext_meet.css"
# web_include_js = "/assets/erpnext_meet/js/erpnext_meet.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Meeting" : "public/js/meeting.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "erpnext_meet/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "erpnext_meet.erpnext_meet.utils.jinja_methods",
# 	"filters": "erpnext_meet.erpnext_meet.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "erpnext_meet.install.before_install"
# after_install = "erpnext_meet.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "erpnext_meet.uninstall.before_uninstall"
# after_uninstall = "erpnext_meet.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "erpnext_meet.erpnext_meet.utils.before_app_install"
# after_app_install = "erpnext_meet.erpnext_meet.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "erpnext_meet.erpnext_meet.utils.before_app_uninstall"
# after_app_uninstall = "erpnext_meet.erpnext_meet.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "erpnext_meet.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
    "hourly": [
        "erpnext_meet.tasks.hourly"
    ]
}


