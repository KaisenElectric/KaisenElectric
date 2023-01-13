from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProductPackaging(models.Model):
    _inherit = "product.packaging"

    _sql_constraints = [
        (
            "logismart_product_code_uniq",
            "unique(logismart_product_code)",
            "Only one Logismart Product Code can be linked!",
        ),
    ]

    logismart_product_code = fields.Char(string="Logismart product code")
    stock_quant_package_ids = fields.One2many(
        comodel_name="stock.quant.package", inverse_name="product_packaging_id", string="Stock Quant Packages"
    )
    stock_quant_package_id = fields.Many2one(
        comodel_name="stock.quant.package",
        compute="_compute_stock_quant_package_id",
        inverse="_inverse_stock_quant_package_id",
        string="Stock Quant Package",
        store=True,
    )

    @api.model
    def create(self, values):
        record_id = super().create(values)
        if not record_id.stock_quant_package_id:
            record_id.stock_quant_package_id = self.env["stock.quant.package"].create(
                {
                    "name": record_id.name,
                }
            )
        return record_id

    @api.depends("stock_quant_package_ids")
    def _compute_stock_quant_package_id(self):
        """Computes stock_quant_package_id by stock_quant_package_ids"""
        for record_id in self:
            record_id.stock_quant_package_id = record_id.stock_quant_package_ids[:1]

    def _inverse_stock_quant_package_id(self):
        """Inverses stock_quant_package_id, adds self in stock_quant_package_id"""
        for record_id in self:
            record_id.stock_quant_package_id.product_packaging_id = self

    # @api.constrains("logismart_product_code")
    # def _check_logismart_product_code(self):
    #     """Checks if product code exists in logismart system"""
    #     for record_id in self:
    #         if record_id.logismart_product_code:
    #             record_id.check_product_code_in_logismart()

    @api.constrains("name")
    def _check_name(self):
        """Changes name in stock_quant_package_id"""
        for record_id in self:
            if record_id.stock_quant_package_id:
                record_id.with_context(force_edit_stock_quant_package=True).stock_quant_package_id.name = record_id.name

    # @api.onchange("logismart_product_code")
    # def _onchange_logismart_product_code(self):
    #     """Checks if product code exists in logismart system"""
    #     for record_id in self:
    #         record_id.check_product_code_in_logismart()

    def check_product_code_in_logismart(self):
        """Checks if product code exists in logismart system"""
        self.ensure_one()
        product_code = self.logismart_product_code
        if product_code and not self.is_exist_product_code_in_logismart(product_code):
            raise ValidationError("Product code not exist in Logismart")

    def is_exist_product_code_in_logismart(self, product_code):
        """Checks if product code exists in logismart system"""
        payload = {
            "product_code": product_code,
        }
        try:
            self.env["res.config.settings"].send_request_to_logismart("get", "/products/get", payload)
        except Exception:
            return False
        return True
