from odoo import api, models, fields


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Warehouse"
    )
    average_unit_value = fields.Monetary(
        string="Average Unit Value",
        related="unit_cost",
        store=True,
        group_operator="avg"
    )
    tag_ids = fields.Many2many(
        comodel_name="product.tag",
        relation="product_tag_stock_valuation_layer_rel",
        column1="stock_valuation_layer_id",
        column2="product_tag_id",
        string="Tags",
        manual=True,
        copy=False,
    )

    category_id = fields.Many2one(
        comodel_name="product.category",
        related="product_id.categ_id",
        string="Category",
        store=True,
    )

    def create(self, values):
        result = super().create(values)
        if self.env.context.get("force_period_date") and result.id:
            create_date = self.env.context.get("force_period_date").strftime("%Y-%m-%d %H:%M:%S")
            self._cr.execute("UPDATE stock_valuation_layer SET create_date = %s WHERE id=%s", (create_date, result.id))
        return result
