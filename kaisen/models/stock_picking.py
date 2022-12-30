from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.addons.payment import utils as payment_utils


class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_send_data_to_logismart = fields.Boolean(string="Send data to Logismart", default=True)

    @api.constrains("state")
    def _check_state(self):
        """Checks field product_packaging_qty for integer when moving stock picking to done stage"""
        for record_id in self:
            if record_id.state == "done":
                for move_id in record_id.move_ids_without_package:
                    if not move_id.product_packaging_qty.is_integer():
                        raise UserError("Packaging Quality must be whole number")
                if record_id.picking_type_id.code == "incoming" and record_id.is_send_data_to_logismart:
                    record_id.create_arrival_in_logismart()
                elif record_id.picking_type_id.code == "outgoing" and record_id.is_send_data_to_logismart:
                    record_id.create_order_in_logismart()

    def get_products_for_logismart(self):
        """Returns products for logismart"""
        self.ensure_one()
        products = []
        for move_id in self.move_ids_without_package:
            product_code = move_id.get_logismart_product_code()
            if product_code and move_id.product_packaging_qty > 0:
                if not move_id.product_packaging_qty.is_integer():
                    raise UserError("Packaging Quality must be whole number")
                products.append(
                    {
                        "product_code": product_code,
                        "quantity": int(move_id.product_packaging_qty),
                    }
                )
        return products

    def create_arrival_in_logismart(self):
        """Creates arrival in logismart"""
        self.ensure_one()
        products = self.get_products_for_logismart()
        if products:
            payload = {
                "delivery_date": fields.Date.today().strftime("%Y-%m-%d"),
                "products": products,
            }
            self.env["res.config.settings"].send_request_to_logismart("post", "/arrivals/add", payload)

    def create_order_in_logismart(self):
        """Create order in logismart"""
        self.ensure_one()
        products = self.get_products_for_logismart()
        if products:
            if not self.carrier_id:
                raise UserError("Carrier field not filled")
            if not self.carrier_id.logismart_delivery_method:
                raise UserError("You need to fill in Logismart Shipping Method field in Carrier")
            first_name, last_name = payment_utils.split_partner_name(self.partner_id.name)
            delivery = {
                "method": self.carrier_id.logismart_delivery_method,
            }
            payload = {
                "order_code": self.name,
                "products": products,
                "delivery": delivery,
                "customer_code": "348",
                "first_name": first_name,
                "last_name": last_name,
                "email": self.partner_id.email,
                "phone": self.partner_id.phone,
                "address": self.partner_id.street_name,
                "house": self.partner_id.street_number,
                "postcode": self.partner_id.zip,
                "city": self.partner_id.city,
                "country_code": self.partner_id.country_id.code,
                "total": self.sale_id.amount_total,
            }
            self.env["res.config.settings"].send_request_to_logismart("post", "/orders/add", payload)
