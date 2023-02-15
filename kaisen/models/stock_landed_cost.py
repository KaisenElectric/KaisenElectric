from odoo import models, fields, _


class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    name = fields.Char(readonly=False)

    def _get_filtered_targeted_move_ids(self):
        return self._get_targeted_move_ids().filtered(lambda move:
            move.product_id.cost_method in ("fifo", "fifowh", "average")\
            and move.state != "cancel"\
            and move.product_qty
                                                      )
