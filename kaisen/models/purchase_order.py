from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.model
    def _prepare_sale_order_line_data(self, line, company):
        """
        OVERRIDE
        Adds purchase_order_line_ids in line.
        """
        result = super()._prepare_sale_order_line_data(line, company)
        result["purchase_order_line_ids"] = [(6, 0, [line.id])]
        result["product_packaging_id"] = line.product_packaging_id.id
        result["product_packaging_qty"] = line.product_packaging_qty
        return result
