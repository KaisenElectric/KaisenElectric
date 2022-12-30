from odoo import models, fields


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    logismart_delivery_method = fields.Integer(string="Logismart Delivery Method")
