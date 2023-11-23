/** @odoo-module **/

import accountReportsWidget from 'account_reports.account_report';

accountReportsWidget.include({
    events: _.extend({}, accountReportsWidget.prototype.events, {
        'click .o_control_panel input[name="partners_include_exclude"]': '_toggle_partners_include_exclude',
    }),

    _toggle_partners_include_exclude: function (ev) {
        let choose_value = ev.target.value != 'exclude';
        if (choose_value != this.report_options.partners_include_exclude) {
            this.report_options.partners_include_exclude = choose_value;
            this.reload().then(() => {
                this.$searchview_buttons.find('.account_partner_filter').click();
            });
        }
    },

});
