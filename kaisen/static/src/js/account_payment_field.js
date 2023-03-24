odoo.define("kaisen.ShowPaymentLineWidgetKaisen", function (require) {
    "use strict";

    let ShowPaymentLineWidget = require("account.payment").ShowPaymentLineWidget;

    ShowPaymentLineWidget.include({

        _onOpenPayment: function (event) {
            let self = this;
            this._rpc({
                model: "account.move",
                method: "check_account_user_group",
                args: [],
            }).then(function (result) {
                var paymentId = parseInt($(event.target).attr("payment-id"));
                var moveId = parseInt($(event.target).attr("move-id"));
                var resModel;
                var id;
                if (paymentId !== undefined && !isNaN(paymentId)) {
                    resModel = "account.payment";
                    id = paymentId;
                } else if (moveId !== undefined && !isNaN(moveId)) {
                    resModel = "account.move";
                    id = moveId;
                }
                if (!self.viewAlreadyOpened && resModel && id && result) {
                    self.viewAlreadyOpened = true;
                    self.do_action({
                        type: "ir.actions.act_window",
                        res_model: resModel,
                        res_id: id,
                        views: [[false, "form"]],
                        target: "current"
                    });
                }
            });
        },
    });

});
