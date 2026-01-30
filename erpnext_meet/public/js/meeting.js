
// Standard reliable way for Meeting DocType
// Version 15 Fix applied
frappe.ui.form.on("Meeting", {
    refresh: function (frm) {
        console.log("ERPNext Meet v15.1 Loaded");
        setup_video_button(frm);
    }
});

function setup_video_button(frm) {
    if (!frm || !frm.doc) return;

    // Only for Meeting (or docs with status/session_id)
    if (frm.doctype !== "Meeting") return;

    // Remove existing buttons
    frm.remove_custom_button('Join Meeting');
    frm.remove_custom_button('End Meeting');

    if ((frm.doc.status === "Active" || frm.doc.status === "Waiting") && frm.doc.session_id) {
        let room_name = `Meet-${frm.doc.reference_doctype || 'Instant'}-${frm.doc.reference_docname || 'Meeting'}-${frm.doc.session_id}`.replace(/ /g, "_");

        // Fix for Instant
        if (!frm.doc.reference_doctype) {
            room_name = `Meet-Instant-${frm.doc.session_id}`;
        }

        // --- RSVP LOGIC ---
        let current_user_participant = (frm.doc.participants || []).find(p => p.user === frappe.session.user);
        let status = current_user_participant ? current_user_participant.invitation_status : null;

        // If Pending, show Accept/Reject
        if (status === "Pending" && frm.doc.host !== frappe.session.user) {
            let accept_btn = frm.add_custom_button('Accept', function () {
                frappe.call({
                    method: 'erpnext_meet.erpnext_meet.api.update_invitation_status',
                    args: { room_name: room_name, status: 'Accepted' },
                    callback: function (r) {
                        if (r.message) {
                            frappe.show_alert({ message: "Invitation Accepted", indicator: 'green' });
                            frm.reload_doc();
                        }
                    }
                });
            });
            accept_btn.addClass("btn-primary");

            let reject_btn = frm.add_custom_button('Reject', function () {
                frappe.confirm("Are you sure you want to reject this meeting invite?", () => {
                    frappe.call({
                        method: 'erpnext_meet.erpnext_meet.api.update_invitation_status',
                        args: { room_name: room_name, status: 'Rejected' },
                        callback: function (r) {
                            if (r.message) {
                                frappe.show_alert({ message: "Invitation Rejected", indicator: 'orange' });
                                frm.reload_doc();
                            }
                        }
                    });
                });
            });
            reject_btn.addClass("btn-danger");
        }
        else if (status === "Rejected") {
            frm.dashboard.add_comment("Warning", "You have rejected this invitation.");
        }
        // If Accepted or Host, show Join Button
        else if (status === "Accepted" || frm.doc.host === frappe.session.user) {
            let join_btn = frm.add_custom_button('Join Meeting', function () {
                join_meeting_direct(room_name);
            });
            join_btn.addClass("btn-danger");
        }

        if (frm.doc.host === frappe.session.user) {
            frm.add_custom_button('End Meeting', function () {
                frappe.confirm('End this meeting?', () => {
                    frappe.call({
                        method: 'erpnext_meet.erpnext_meet.api.end_meeting',
                        args: { room_name: room_name },
                        callback: function () {
                            frm.reload_doc();
                        }
                    });
                });
            });
        }
    }
}

function join_meeting_direct(room_name) {
    let url = frappe.urllib.get_full_url("/api/method/erpnext_meet.erpnext_meet.api.join_room?room_name=" + room_name);
    window.open(url, '_blank');
}

function start_meeting() {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'User',
            fields: ['name', 'full_name', 'email'],
            filters: {
                'enabled': 1,
                'user_type': 'System User',
                'name': ['!=', 'Guest']
            },
            limit_page_length: 500,
            order_by: 'full_name asc'
        },
        callback: function (r) {
            if (r.message) {
                let users = r.message;
                let d = new frappe.ui.Dialog({
                    title: 'Invite Participants',
                    fields: [
                        {
                            fieldtype: 'HTML',
                            fieldname: 'user_list_html'
                        }
                    ],
                    primary_action_label: 'Start Meeting',
                    primary_action: function () {
                        let selected_users = [];
                        d.$wrapper.find('.meet-user-checkbox:checked').each(function () {
                            selected_users.push($(this).data('user'));
                        });

                        if (selected_users.length === 0) {
                            frappe.msgprint("Please select at least one user.");
                            return;
                        }

                        create_and_join_room(selected_users);
                        d.hide();
                    }
                });

                let html = `
                    <div style="padding: 10px;">
                        <input type="text" class="form-control input-sm" placeholder="Search Name..." id="meet-user-filter" style="margin-bottom: 10px;">
                        <div class="list-group" style="max-height: 400px; overflow-y: auto; border: 1px solid #d1d8dd; border-radius: 4px;" id="meet-user-list-container">
                            ${users.map(u => `
                                <div class="list-group-item meet-user-item" data-search="${(u.full_name || '').toLowerCase()} ${(u.email || '').toLowerCase()}">
                                    <div class="row" style="display: flex; align-items: center;">
                                        <div class="col-xs-1" style="width: 30px;">
                                            <input type="checkbox" class="meet-user-checkbox" data-user="${u.name}">
                                        </div>
                                        <div class="col-xs-11">
                                            <div style="font-weight: bold;">${u.full_name || u.name}</div>
                                            <div class="text-muted small">${u.email}</div>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;

                d.fields_dict.user_list_html.$wrapper.html(html);

                d.$wrapper.find('#meet-user-filter').on('keyup', function () {
                    let val = $(this).val().toLowerCase();
                    d.$wrapper.find('.meet-user-item').each(function () {
                        let text = $(this).data('search');
                        $(this).toggle(text.indexOf(val) !== -1);
                    });
                });

                d.$wrapper.find('.meet-user-item').on('click', function (e) {
                    if (e.target.type !== 'checkbox') {
                        let checkbox = $(this).find('input[type="checkbox"]');
                        checkbox.prop('checked', !checkbox.prop('checked'));
                    }
                });

                d.show();
            }
        }
    });
}

function create_and_join_room(invited_users) {
    frappe.call({
        method: "erpnext_meet.erpnext_meet.api.create_room",
        args: {
            doctype: cur_frm ? cur_frm.doctype : null,
            docname: cur_frm ? cur_frm.docname : null
        },
        callback: function (r) {
            if (r.message) {
                let room_data = r.message;
                if (invited_users && invited_users.length > 0) {
                    frappe.call({
                        method: "erpnext_meet.erpnext_meet.api.invite_users",
                        args: {
                            users: invited_users,
                            room_name: room_data.room_name,
                            doctype: cur_frm ? cur_frm.doctype : "Meeting",
                            docname: cur_frm ? cur_frm.docname : room_data.session_name
                        }
                    });
                }
                if (room_data.join_link) {
                    window.open(room_data.join_link, '_blank');
                }
            }
        }
    });
}
