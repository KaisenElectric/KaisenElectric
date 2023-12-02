from odoo import models, api, fields, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    posted_invoice_line_ids = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="move_id",
        string="Invoice lines",
        copy=False,
        readonly=True,
        domain=[("exclude_from_invoice_tab", "=", False)],
        states={"posted": [("readonly", False)]}
    )
    invoice_payments_widget = fields.Text(
        compute_sudo=True,
    )
    last_payment_date = fields.Date(
        string="Paid On",
        compute="_compute_last_payment_date",
        store=True,
    )

    @api.depends("move_type", "payment_state", "line_ids.amount_residual")
    def _compute_last_payment_date(self):
        """
        Method for calculating the last_payment_date field
        """
        for move_id in self:
            content = move_id._get_reconciled_info_JSON_values()
            date = content[-1].get("date") if content else False
            move_id.write({
                "last_payment_date": date,
            })

    def js_remove_outstanding_partial(self, partial_id):
        """
        Method added logic to check user groups
        """
        self.ensure_one()
        if not self.env.user.has_group("account.group_account_user") or not self.env.user.has_group("account.group_account_manager"):
            raise UserError(_("You have no access rights."))
        return super(AccountMove, self).js_remove_outstanding_partial(partial_id)

    def js_assign_outstanding_line(self, line_id):
        """
        Method added logic to check user groups
        """
        self.ensure_one()
        if not self.env.user.has_group("account.group_account_user") or not self.env.user.has_group("account.group_account_manager"):
            raise UserError(_("You have no access rights."))
        return super(AccountMove, self).js_assign_outstanding_line(line_id)

    @api.model
    def check_account_user_group(self):
        """
        Method added logic to check user groups
        """
        if not self.env.user.has_group("account.group_account_user") or not self.env.user.has_group("account.group_account_manager"):
            raise UserError(_("You have no access rights."))
        return True

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

    def _move_autocomplete_invoice_lines_values(self):
        values = super()._move_autocomplete_invoice_lines_values()
        values.pop("posted_invoice_line_ids", None)
        return values

    def button_draft(self):
        if len(self) == 1:
            sale_order_ids = self.invoice_line_ids.sale_line_ids.order_id
            if (self.env.user.has_group('kaisen.group_personal_lead') and sale_order_ids.user_id == self.env.user)\
                    or (self.env.user.has_group('kaisen.group_team_lead')
                        and set(sale_order_ids.team_id.ids) ^ set(self.env.user.crm_team_ids.ids)):
                return super(AccountMove, self.sudo()).button_draft()
        return super().button_draft()
