from odoo import models, fields, _


class AdjustmentLines(models.Model):
    _inherit = "stock.valuation.adjustment.lines"

    def _create_stock_valuation_layer(self, linked_layer, cost_to_add):
        self.ensure_one()
        cost_id = self.cost_id
        svl_data = {
                    "value": cost_to_add,
                    "unit_cost": 0,
                    "quantity": 0,
                    "remaining_qty": 0,
                    "stock_valuation_layer_id": linked_layer.id,
                    "description": cost_id.name,
                    "stock_move_id": self.move_id.id,
                    "product_id": self.move_id.product_id.id,
                    "stock_landed_cost_id": cost_id.id,
                    "company_id": cost_id.company_id.id,
                }
        if self.move_id.product_id.cost_method == "fifowh" and self.move_id.location_dest_id.warehouse_id:
            svl_data["warehouse_id"] = self.move_id.location_dest_id.warehouse_id.id
        return self.env["stock.valuation.layer"].create(svl_data)
