from odoo import models, api
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.constrains("state")
    def _check_state(self):
        """Checks field product_packaging_qty for integer when moving stock picking to done stage"""
        for record_id in self:
            for move_id in record_id.move_ids_without_package:
                if record_id.state == "done" and not move_id.product_packaging_qty.is_integer():
                    raise UserError("Packaging Quantity must be an integer")
