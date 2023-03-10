from odoo import models, api, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def _get_default_bank(self):
        """Method set default value for company_recipient_bank_id"""
        bank_id = self.env.company.partner_id.bank_ids[:1]
        return bank_id

    company_recipient_bank_id = fields.Many2one(comodel_name="res.partner.bank", string="Company Recipient Bank",
                                                help="Bank Account Number to which the invoice will be paid.",
                                                default=_get_default_bank, check_company=True)

    @api.onchange("company_id")
    def _onchange_company_id(self):
        """
        Method adds domain for company_recipient_bank_id field depends on company_id.
        """
        for record in self:
            domain = [("partner_id", "=", record.company_id.partner_id.id)]
            return {
                "domain": {"company_recipient_bank_id": domain},
            }

    @api.model
    def _prepare_purchase_order_line_data(self, so_line, date_order, company):
        """OVERRIDE
        Adds sale_order_line_id in line.
        """
        result = super()._prepare_purchase_order_line_data(so_line, date_order, company)
        result["sale_order_line_id"] = so_line.id
        result["product_packaging_id"] = so_line.product_packaging_id.id
        result["price_unit"] = so_line.price_unit
        result["product_packaging_qty"] = so_line.product_packaging_qty
        return result
