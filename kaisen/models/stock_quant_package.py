from odoo import models, fields, api
from odoo.exceptions import UserError


class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"

    _sql_constraints = [
        ("product_packaging_id_uniq", "unique(product_packaging_id)", "Only one product packaging can be linked!"),
    ]

    product_packaging_id = fields.Many2one(comodel_name="product.packaging", string="Product Packaging")
    location_id = fields.Many2one(string="Location", compute=False, readonly=False
    )
    company_id = fields.Many2one(string="Company", compute=False, readonly=False
    )

    @api.depends('quant_ids.package_id', 'quant_ids.location_id', 'quant_ids.company_id', 'quant_ids.owner_id',
                 'quant_ids.quantity', 'quant_ids.reserved_quantity')
    def _compute_package_info(self):
        for package in self:
            values = {'location_id': False, 'owner_id': False}
            if package.quant_ids:
                values['location_id'] = package.quant_ids[0].location_id
                if all(q.owner_id == package.quant_ids[0].owner_id for q in package.quant_ids):
                    values['owner_id'] = package.quant_ids[0].owner_id
                if all(q.company_id == package.quant_ids[0].company_id for q in package.quant_ids):
                    values['company_id'] = package.quant_ids[0].company_id
            package.owner_id = values['owner_id']

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
