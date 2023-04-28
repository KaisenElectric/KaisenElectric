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
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse", string="Warehouse", compute="_compute_stock_warehouse_id", store=True
    )

    @api.depends("move_id.stock_valuation_layer_ids.warehouse_id")
    def _compute_stock_warehouse_id(self):
        """
        Computes warehouse for account move line by valuation layer in account move.
        It is assumed that in one Account Move, all Valuation Layers belong to one warehouse.
        """
        for record_id in self:
            record_id.warehouse_id = record_id.move_id.stock_valuation_layer_ids.mapped("warehouse_id")[:1]

    @api.depends("sale_line_ids", "sale_line_ids.order_id", "sale_line_ids.order_id.picking_ids")
    def _compute_stock_picking_names(self):
        """
        Method compute stock_picking_names depends on name from related sale_order.stock_picking.
        """
        for record in self:
            picking_ids = record.sale_line_ids.order_id.picking_ids.filtered(lambda p_id: p_id.state != "cancel")
            stock_picking_names = ", ".join(picking_ids.mapped("name"))
            record.write(
                {
                    "stock_picking_names": stock_picking_names,
                }
            )
