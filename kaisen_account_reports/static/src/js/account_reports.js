/** @odoo-module **/

import {_t} from 'web.core';
import accountReportsWidget from 'account_reports.account_report';
import M2MFilters from '@kaisen_account_reports/js/m2m_filters';

accountReportsWidget.include({
    events: _.extend({}, accountReportsWidget.prototype.events, {
        'click .o_control_panel input[name="partners_include_exclude"]': '_toggle_partners_include_exclude',
    }),
    custom_events: _.extend({}, accountReportsWidget.prototype.custom_events, {
        'value_changed': '_onValueChanged',
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

    render_searchview_buttons: function() {
        this._super(...arguments);

        // partner saleperson
        if (this.report_options.saleperson) {
            if (!this.M2MFilters_saleperson) {
                let fields = {};
                if ('saleperson_ids' in this.report_options) {
                    fields['saleperson_ids'] = {
                        label: _t('Salepersons'),
                        modelName: 'res.users',
                        value: this.report_options.saleperson_ids.map(Number),
                    };
                }
                if (!_.isEmpty(fields)) {
                    this.M2MFilters_saleperson = new M2MFilters(this, fields);
                    this.M2MFilters_saleperson.appendTo(this.$searchview_buttons.find('.js_account_saleperson_m2m'));
                }
            } else {
                this.$searchview_buttons.find('.js_account_saleperson_m2m').append(this.M2MFilters_saleperson.$el);
            }
        }
    },

    _updateOption: function (option, data) {
        if (data[option] !== undefined) {
            this.report_options[option] = data[option];
            return option;
        }
    },

    _onValueChanged: function (ev) {
        let changed_fields = ['partner_ids', 'partner_categories', 'analytic_accounts',
                              'analytic_tags', 'saleperson_ids'].map(option => this._updateOption(option, ev.data));

        return this.reload().then(() => {
            if (changed_fields.includes('partner_ids'))
                this.$searchview_buttons.find('.account_partner_filter').click();
            if (changed_fields.includes('analytic_accounts') || changed_fields.includes('analytic_tags'))
                this.$searchview_buttons.find('.account_analytic_filter').click();
            if (changed_fields.includes('saleperson_ids'))
                this.$searchview_buttons.find('.account_saleperson_filter').click();
        });
    },

});
