from odoo import models, fields
import xlrd
from base64 import b64decode
from odoo.tests.common import Form
from odoo.exceptions import UserError


class ImportOfCostOfProductsWizard(models.TransientModel):
    _name = "import.of.cost.of.products.wizard"
    _description = "Import of cost of products wizard"

    file = fields.Binary(string="File", required=True, attachment=False)

    def import_of_cost_of_products(self):
        book = xlrd.open_workbook(file_contents=b64decode(self.file) or b"")
        sheet = book.sheet_by_index(0)
        for index, row in enumerate(sheet.get_rows()):
            if index == 0:
                continue
            po_form = Form(self.env["purchase.order"])
            partner_id = self.env["res.partner"].search([("name", "=", row[2].value)], limit=1)
            if not partner_id:
                raise UserError(f"Vendor {row[2].value} was not found in line {index + 1}")
            po_form.partner_id = partner_id
            currency_id = self.env["res.currency"].search([("name", "=", row[8].value)], limit=1)
            if not currency_id:
                raise UserError(f"Currency {row[8].value} was not found in line {index + 1}")
            po_form.currency_id = currency_id
            company_id = self.env["res.company"].search([("name", "=", row[5].value)], limit=1)
            if not company_id:
                raise UserError(f"Company {row[5].value} was not found in line {index + 1}")
            po_form.company_id = company_id
            picking_type_id = self.env["stock.picking.type"].search(
                [
                    ("code", "=", "incoming"),
                    ("warehouse_id.company_id", "=", company_id.id),
                    ("warehouse_id.name", "=", row[4].value),
                ],
                limit=1,
            )
            if not picking_type_id:
                raise UserError(f"Delivery with {row[4].value} warehouse was not found in line {index + 1}")
            po_form.picking_type_id = picking_type_id
            with po_form.order_line.new() as line:
                product_id = self.env["product.product"].search([("name", "=", row[0].value.split("/")[0])], limit=1)
                if not product_id:
                    raise UserError(f"Product {row[0].value.split('/')[0]} was not found in line {index + 1}")
                line.product_id = product_id
                product_qty = int(row[6].value)
                if not product_qty:
                    raise UserError(f"The quantity of the product was not specified in line {index + 1}")
                line.product_qty = product_qty
                price_unit = float(row[7].value)
                if not price_unit:
                    raise UserError(f"The unit price was not specified in line {index + 1}")
                line.price_unit = price_unit
                packaging_id = product_id.packaging_ids.filtered(lambda x: x.qty == float(row[3].value))[:1]
                if not packaging_id:
                    raise UserError(f"Packaging {row[3].value} was not found in line {index + 1}")
                line.product_packaging_id = packaging_id
            po_id = po_form.save()
            po_id.button_confirm()
            for picking_id in po_id.picking_ids:
                for move_id in picking_id.move_lines:
                    move_id.quantity_done = move_id.product_uom_qty
                wizard_action = picking_id.button_validate()
                if wizard_action is not True:
                    Form(self.env[wizard_action["res_model"]].with_context(wizard_action["context"])).save().process()
        return self.env.ref("stock_account.stock_valuation_layer_action").read()[0]
