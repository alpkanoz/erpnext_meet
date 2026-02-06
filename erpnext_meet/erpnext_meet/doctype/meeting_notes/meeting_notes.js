// Copyright (c) 2026, Alpkan Öztürk and contributors
// For license information, please see license.txt

frappe.ui.form.on("Meeting Notes", {
    refresh(frm) {
        if (frm.doc.transcription_status === "Completed" && frm.doc.raw_transcript) {
            // Add export buttons
            frm.add_custom_button(__('Export as TXT'), function () {
                frappe.call({
                    method: 'erpnext_meet.erpnext_meet.api.export_meeting_notes',
                    args: {
                        meeting_notes_name: frm.doc.name,
                        format: 'txt'
                    },
                    callback: function (r) {
                        if (r.message) {
                            window.open(r.message);
                        }
                    }
                });
            }, __('Export'));

            frm.add_custom_button(__('Export as DOCX'), function () {
                frappe.call({
                    method: 'erpnext_meet.erpnext_meet.api.export_meeting_notes',
                    args: {
                        meeting_notes_name: frm.doc.name,
                        format: 'docx'
                    },
                    callback: function (r) {
                        if (r.message) {
                            window.open(r.message);
                        }
                    }
                });
            }, __('Export'));

            frm.add_custom_button(__('Export as PDF'), function () {
                frappe.call({
                    method: 'erpnext_meet.erpnext_meet.api.export_meeting_notes',
                    args: {
                        meeting_notes_name: frm.doc.name,
                        format: 'pdf'
                    },
                    callback: function (r) {
                        if (r.message) {
                            window.open(r.message);
                        }
                    }
                });
            }, __('Export'));
        }

        // Show transcript preview
        if (frm.doc.raw_transcript) {
            try {
                let transcript = JSON.parse(frm.doc.raw_transcript);
                let preview = transcript.slice(0, 10).map(item => {
                    let timestamp = `[${String(Math.floor(item.start / 60)).padStart(2, '0')}:${String(Math.floor(item.start % 60)).padStart(2, '0')}]`;
                    return `<p><span class="text-muted">${timestamp}</span> <strong>${item.speaker || 'Speaker'}:</strong> ${item.text}</p>`;
                }).join('');

                if (transcript.length > 10) {
                    preview += `<p class="text-muted">... and ${transcript.length - 10} more segments</p>`;
                }

                frm.set_df_property('raw_transcript', 'description', preview);
            } catch (e) {
                // Invalid JSON
            }
        }
    }
});
