from odoo import models, api, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    posted_invoice_line_ids = fields.One2many(comodel_name="account.move.line", inverse_name="move_id",
                                              string="Invoice lines", copy=False, readonly=True,
                                              domain=[("exclude_from_invoice_tab", "=", False)],
                                              states={"posted": [("readonly", False)]})

    @api.onchange("name", "highest_name")
    def _onchange_name_warning(self):
        """
        OVERRIDE
        Does not return a warning.
        """
        super()._onchange_name_warning()

    def button_create_landed_costs(self):
        """Override method to change passing account_id"""
        self.ensure_one()
        landed_costs_lines = self.line_ids.filtered(lambda line: line.is_landed_costs_line)

        landed_costs = self.env["stock.landed.cost"].create({
            "vendor_bill_id": self.id,
            "cost_lines": [(0, 0, {
                "product_id": l.product_id.id,
                "name": l.product_id.name,
                "account_id": l.account_id.id,
                "price_unit": l.currency_id._convert(l.price_subtotal, l.company_currency_id, l.company_id, l.move_id.date),
                "split_method": l.product_id.split_method_landed_cost or "equal",
            }) for l in landed_costs_lines],
        })
        action = self.env["ir.actions.actions"]._for_xml_id("stock_landed_costs.action_stock_landed_cost")
        return dict(action, view_mode="form", res_id=landed_costs.id, views=[(False, "form")])
