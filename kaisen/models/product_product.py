from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.depends('stock_valuation_layer_ids')
    @api.depends_context('to_date', 'company', 'warehouse')
    def _compute_value_svl(self):
        """Compute `value_svl` and `quantity_svl`."""
        if not self.env.context.get('warehouse'):
            super()._compute_value_svl()
            return None

        company_id = self.env.company.id
        domain = [
            ('product_id', 'in', self.ids),
            ('company_id', '=', company_id),
            # start changes
            ('warehouse_id', '=', self.env.context['warehouse']),
            # end changes
        ]
        if self.env.context.get('to_date'):
            to_date = fields.Datetime.to_datetime(self.env.context['to_date'])
            domain.append(('create_date', '<=', to_date))
        groups = self.env['stock.valuation.layer'].read_group(domain, ['value:sum', 'quantity:sum'], ['product_id'], orderby='id')
        products = self.browse()
        for group in groups:
            product = self.browse(group['product_id'][0])
            product.value_svl = self.env.company.currency_id.round(group['value'])
            product.quantity_svl = group['quantity']
            products |= product
        remaining = (self - products)
        remaining.value_svl = 0
        remaining.quantity_svl = 0
