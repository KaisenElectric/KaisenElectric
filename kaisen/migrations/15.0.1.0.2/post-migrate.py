from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """
    Migration for trigger compute method to change last_payment_date
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    move_ids = env["account.move"].search([("payment_state", "in", ("in_payment", "paid", "partial"))])
    move_ids._compute_last_payment_date()
