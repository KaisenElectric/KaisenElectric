from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    comments = fields.Char(
        string="Comments",
    )
    last_payment_date = fields.Date(
        related="move_id.last_payment_date",
        store=True,
    )
    stock_picking_names = fields.Char(
        string="Delivery",
        compute="_compute_stock_picking_names",
        store=True,
    )

    @api.depends("sale_line_ids", "sale_line_ids.order_id", "sale_line_ids.order_id.picking_ids")
    def _compute_stock_picking_names(self):
        """
        Method compute stock_picking_names depends on name from related sale_order.stock_picking.
        """
        for record in self:
            picking_ids = record.sale_line_ids.order_id.picking_ids.filtered(lambda p_id: p_id.state != "cancel")
            stock_picking_names = ", ".join(picking_ids.mapped("name"))
            record.write({
                "stock_picking_names": stock_picking_names,
            })
