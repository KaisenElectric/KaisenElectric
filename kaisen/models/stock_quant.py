from odoo import models, fields, api
from odoo.tools.float_utils import float_round


class StockQuant(models.Model):
    _inherit = "stock.quant"

    on_hand_package_quantity = fields.Float(
        string="On Hand Package Quantity",
        compute="_compute_on_hand_package_quantity",
    )
    available_package_quantity = fields.Float(
        string="Available Package Quantity",
        compute="_compute_available_package_quantity",
    )
    package_quantity = fields.Float(
        string="Package Quantity",
        compute="_compute_package_quantity",
    )
    counted_package_quantity = fields.Float(
        string="Counted Package Quantity",
        compute="_compute_counted_package_quantity",
    )
    tag_ids = fields.Many2many(
        comodel_name="product.tag",
        relation="product_tag_stock_quant_rel",
        column1="stock_quant_id",
        column2="product_tag_id",
        string="Tags",
        manual=True,
        copy=False,
    )

    analytic_account_id = fields.Many2one(
        related="location_id.warehouse_id.analytic_account_id",
        string="Analytic Account",
        store=True,
    )

    @api.depends("inventory_quantity_auto_apply")
    def _compute_on_hand_package_quantity(self):
        """Computes on_hand_package_quantity by inventory_quantity_auto_apply"""
        for record_id in self:
            record_id.on_hand_package_quantity = record_id.compute_package_quantity("inventory_quantity_auto_apply")

    @api.depends("available_quantity")
    def _compute_available_package_quantity(self):
        """Computes available_package_quantity by available_quantity"""
        for record_id in self:
            record_id.available_package_quantity = record_id.compute_package_quantity("available_quantity")

    @api.depends("quantity")
    def _compute_package_quantity(self):
        """Computes package_quantity by quantity"""
        for record_id in self:
            record_id.package_quantity = record_id.compute_package_quantity("quantity")

    @api.depends("inventory_quantity")
    def _compute_counted_package_quantity(self):
        """Computes counted_package_quantity by inventory_quantity"""
        for record_id in self:
            record_id.counted_package_quantity = record_id.compute_package_quantity("inventory_quantity")

    def compute_package_quantity(self, quantity_field_name):
        """Computes package quantity by quantity field and packaging qty"""
        self.ensure_one()
        packaging_id = self.package_id.product_packaging_id
        quantity = getattr(self, quantity_field_name)
        if quantity > 0 and packaging_id.qty > 0:
            return float_round(quantity / packaging_id.qty,
                               precision_rounding=packaging_id.product_uom_id.rounding or 0.01)
        return 0
