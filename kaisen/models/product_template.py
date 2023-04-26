from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    tag_ids = fields.Many2many(
        comodel_name="product.tag",
        string="Tags",
        inverse="_inverse_tag_ids",
    )

    def _inverse_tag_ids(self):
        """
        Method rewrite tags in quants and valuations
        """
        for record in self:
            with self.env.cr.savepoint():
                self.delete_values()
                if len(record.tag_ids) > 0:
                    self.insert_values()
            self.env.cr.commit()

    def delete_values(self):
        """
        Method delete values from stock.valuation.layer and stock.quant
        """
        self.ensure_one()
        self.env.cr.execute(
            """
            DELETE FROM product_tag_product_template_rel
            WHERE product_template_id = %(product_template_id)s;

            DELETE FROM product_tag_stock_quant_rel
            WHERE stock_quant_id IN (
                SELECT sq.id
                FROM stock_quant sq
                JOIN product_product pp ON sq.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                WHERE pt.id = %(product_template_id)s
            );

            DELETE FROM product_tag_stock_valuation_layer_rel
            WHERE stock_valuation_layer_id IN (
                SELECT svl.id
                FROM stock_valuation_layer svl
                JOIN product_product pp ON svl.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                WHERE pt.id = %(product_template_id)s
            );
            """, {
                "product_template_id": self.id,
            }
        )

    def insert_values(self):
        """
        Method insert values into stock.valuation.layer and stock.quant
        """
        self.ensure_one()
        self.env.cr.execute(
            """
            INSERT INTO product_tag_product_template_rel (product_template_id, product_tag_id)
            SELECT %(product_template_id)s, unnest(ARRAY[%(tag_ids)s]);
        
            INSERT INTO product_tag_stock_quant_rel (product_tag_id, stock_quant_id)
            SELECT unnest(ARRAY[%(tag_ids)s]), sq.id 
            FROM stock_quant sq
            JOIN product_product pp ON sq.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            WHERE pt.id = %(product_template_id)s;
        
            INSERT INTO product_tag_stock_valuation_layer_rel (product_tag_id, stock_valuation_layer_id)
            SELECT unnest(ARRAY[%(tag_ids)s]), svl.id 
            FROM stock_valuation_layer svl
            JOIN product_product pp ON svl.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            WHERE pt.id = %(product_template_id)s;
            """, {
                "product_template_id": self.id,
                "tag_ids": self.tag_ids.ids,
            }
        )
