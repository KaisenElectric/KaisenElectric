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
