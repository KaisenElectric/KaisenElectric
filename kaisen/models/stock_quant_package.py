from odoo import models, fields
from odoo.exceptions import UserError


class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"

    _sql_constraints = [
        ("product_packaging_id_uniq", "unique(product_packaging_id)", "Only one product packaging can be linked!"),
    ]

    product_packaging_id = fields.Many2one(comodel_name="product.packaging", string="Product Packaging")

    def write(self, values):
        """Blocks editing of record name if it is needed for integration with Logismart"""
        for record in self:
            if (
                values.get("name")
                and record.product_packaging_id.logismart_product_code
                and not self.env.context.get("force_edit_stock_quant_package")
            ):
                values.pop("name")
        return super().write(values)

    def unlink(self):
        """Blocks deletion of a record if it is needed for integration with Logismart"""
        for record in self:
            if record.product_packaging_id.logismart_product_code:
                raise UserError("You cannot edit record because it is used in integration with Logismart")
        return super().unlink()
