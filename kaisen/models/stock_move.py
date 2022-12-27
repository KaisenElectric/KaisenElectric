from odoo import models, fields
from odoo.tools.float_utils import float_round


class StockMove(models.Model):
    _inherit = "stock.move"

    product_packaging_qty = fields.Float(string="Packaging Quantity", compute="_compute_product_packaging_qty")

    def _compute_product_packaging_qty(self):
        """Computes product_packaging_qty by qty in packaging and product qty"""
        for record_id in self:
            if record_id.product_packaging_id.qty:
                packaging_uom_id = record_id.product_packaging_id.product_uom_id
                if record_id.picking_id.picking_type_id.code == "incoming" and record_id.quantity_done:
                    record_id.product_packaging_qty = float_round(
                        record_id.quantity_done / record_id.product_packaging_id.qty,
                        precision_rounding=packaging_uom_id.rounding)
                elif record_id.picking_id.picking_type_id.code == "outgoing" and record_id.forecast_availability:
                    record_id.product_packaging_qty = float_round(
                        record_id.forecast_availability / record_id.product_packaging_id.qty,
                        precision_rounding=packaging_uom_id.rounding)
                elif record_id.picking_id.picking_type_id.code == "outgoing" and record_id.quantity_done:
                    record_id.product_packaging_qty = float_round(
                        record_id.quantity_done / record_id.product_packaging_id.qty,
                        precision_rounding=packaging_uom_id.rounding)
                else:
                    record_id.product_packaging_qty = float_round(
                        record_id.product_qty / record_id.product_packaging_id.qty,
                        precision_rounding=packaging_uom_id.rounding)
            else:
                record_id.product_packaging_qty = 0
