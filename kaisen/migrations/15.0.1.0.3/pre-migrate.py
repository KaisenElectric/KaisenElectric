from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """
    Migration remove rule
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    rule_ids = env["ir.rule"].search([("name", "=", "Own Customers Only Transfers")])
    rule_ids.unlink()
