from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    users =[(4, user.id) for user in env.ref("stock.group_stock_user").users]
    env.ref("kaisen.group_sale_partners").users = users
