odoo.define("kaisen.KaisenView", function (require) {
    "use strict";

    const FormController = require("web.FormController");
    const FormView = require("web.FormView");
    const viewRegistry = require("web.view_registry");
    const Dialog = require("web.Dialog");
    const core = require("web.core");
    const _t = core._t;

    let relational_fields = require("web.relational_fields");
    let FieldMany2ManyTags = relational_fields.FieldMany2ManyTags;

    FieldMany2ManyTags.include({

        async reset(record, ev) {
            const fieldName = this.field.name;
            const fieldArr = ["tax_id", "tax_ids"];
            if (fieldArr.includes(fieldName) && ev && ev.data.changes && (ev.data.changes.tax_id || ev.data.changes.tax_ids)) {
                this.trigger_up("open_tax_wizard");
            }
            this._super(...arguments);
        },

    });

    let KaisenFormController = FormController.extend({
        custom_events: _.extend({}, FormController.prototype.custom_events, {
            open_discount_wizard: "_onOpenDiscountWizard",
            open_tax_wizard: "_onOpenTaxWizard",
        }),

        // -------------------------------------------------------------------------
        // Handlers
        // -------------------------------------------------------------------------

        _onOpenDiscountWizard(ev) {
            let orderLines = [];
            let changes = {};
            const modelName = this.modelName;
            const rendererStateData = this.renderer.state.data;

            if (modelName === "account.move") {
                orderLines = rendererStateData.invoice_line_ids.data.filter(line => !line.data.display_type);
            } else {
                orderLines = rendererStateData.order_line.data.filter(line => !line.data.display_type);
            }

            const recordData = ev.target.recordData;
            if (recordData.discount === orderLines[0].data.discount) return;

            const isEqualDiscount = orderLines.slice(1).every(line => line.data.discount === recordData.discount);

            if (orderLines.length >= 3 && recordData.sequence === orderLines[0].data.sequence && isEqualDiscount) {
                Dialog.confirm(this, _t("Do you want to apply this discount to all order lines?"), {
                    confirm_callback: () => {
                        const discount = orderLines[0].data.discount;
                        const operation = modelName === "account.move" ? "invoice_line_ids" : "order_line";

                        orderLines.slice(1).forEach((line) => {
                            changes = {
                                [operation]: {
                                    operation: "UPDATE",
                                    id: line.id,
                                    data: {
                                        discount: discount,
                                    },
                                },
                            };

                            this.trigger_up("field_changed", {
                                dataPointID: this.renderer.state.id,
                                changes: changes,
                            });
                        });
                    },
                });
            }
        },

        _onOpenTaxWizard(ev) {
            const modelName = this.modelName;
            const rendererStateData = this.renderer.state.data;
            const recordData = ev.target.recordData;

            let changes = {};
            let orderLines = [];
            let currentTaxIDS = {};

            if (modelName === "account.move") {
                orderLines = rendererStateData.invoice_line_ids.data.filter(line => !line.data.display_type);
                currentTaxIDS = orderLines[0].data.tax_ids.res_ids;
                if (recordData.tax_ids == orderLines[0].data.tax_ids) return;
            } else {
                orderLines = rendererStateData.order_line.data.filter(line => !line.data.display_type);
                currentTaxIDS = orderLines[0].data.tax_id.res_ids;
                if (recordData.tax_id == orderLines[0].data.tax_id) return;
            }

            if (orderLines.length >= 3 && recordData.sequence === orderLines[0].data.sequence) {
                Dialog.confirm(this, _t("Do you want to apply this tax to all order lines?"), {
                    confirm_callback: () => {
                        const operation = modelName === "account.move" ? "invoice_line_ids" : "order_line";
                        const taxField = modelName === "account.move" ? "tax_ids" : "tax_id";

                        orderLines.slice(1).forEach((line) => {
                            changes = {
                                [operation]: {
                                    operation: "UPDATE",
                                    id: line.id,
                                    data: {
                                        [taxField]: {
                                            operation: 'MULTI',
                                            commands: [{
                                                operation: 'REPLACE_WITH',
                                                ids: currentTaxIDS,
                                            }]
                                        }
                                    },
                                },
                            };

                            this.trigger_up("field_changed", {
                                dataPointID: this.renderer.state.id,
                                changes: changes,
                            });
                        });
                    },
                });
            }
        },

    });

    const KaisenView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: KaisenFormController,
        }),
    });

    viewRegistry.add("kaisen_form", KaisenView);

    return KaisenView;

});
