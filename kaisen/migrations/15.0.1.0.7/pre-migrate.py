from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref("kaisen.own_customers_only_transfers").groups = [(3, env.ref("stock.group_stock_user").id)]
