// Copyright (c) 2024, Pars and contributors
// For license information, please see license.txt

frappe.ui.form.on('Meeting Settings', {
    refresh: function (frm) {
        frm.add_custom_button('Generate Config Files', function () {
            frappe.call({
                method: 'erpnext_meet.erpnext_meet.utils.config_generator.generate_jitsi_config',
                callback: function (r) {
                    if (r.message) {
                        download_file("config.js", r.message["config.js"]);
                        setTimeout(() => {
                            download_file("interface_config.js", r.message["interface_config.js"]);
                        }, 1000); // Delay to allow both downloads
                        frappe.msgprint("Configuration files generated and downloaded.");
                    }
                }
            });
        });
    }
});

function download_file(filename, text) {
    var element = document.createElement('a');
    element.setAttribute('href', 'data:text/javascript;charset=utf-8,' + encodeURIComponent(text));
    element.setAttribute('download', filename);

    element.style.display = 'none';
    document.body.appendChild(element);

    element.click();

    document.body.removeChild(element);
}
