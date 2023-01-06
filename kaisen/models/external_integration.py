from odoo import models, fields


class ExternalIntegration(models.Model):
    _name = "external.integration"
    _description = "External Integration"

    name = fields.Char(string="Name")
    active = fields.Boolean(string="Active", default=True)
