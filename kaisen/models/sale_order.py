from odoo import models, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

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

    def _prepare_invoice(self):
        """
        Method adds partner_bank_id in AM.
        """
        invoice_vals = super()._prepare_invoice()
        invoice_vals["partner_bank_id"] = self.company_recipient_bank_id.id
        return invoice_vals

    def _get_invoice_grouping_keys(self):
        """
         Method adds partner_bank_id for grouping invoices.
         """
        result = super()._get_invoice_grouping_keys()
        result.append("partner_bank_id")
        return result
