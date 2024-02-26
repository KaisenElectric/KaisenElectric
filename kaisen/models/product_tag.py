from random import randint

from odoo import models, fields


class ProductTag(models.Model):
    _name = "product.tag"
    _description = "Product Tag"

    def _get_default_color(self):
        """
        This function returns a random integer between 1 and 11
        """
        return randint(1, 11)

    name = fields.Char(
        string="Name",
        required=True,
        translate=True,
    )
    color = fields.Integer(
        string="Color",
        default=_get_default_color,
    )

    _sql_constraints = [
        ("name_uniq", "unique (name)", "Tag name already exists !"),
    ]

    def init(self):
        views = ('product_tag_stock_valuation_layer_rel', 'product_tag_stock_quant_rel')
        self.env.cr.execute("""
            SELECT c.relname, c.relkind
            FROM pg_class c
            JOIN pg_namespace n ON (n.oid = c.relnamespace)
            WHERE c.relname IN %s
                AND n.nspname = current_schema
        """, [views])

        query = ""

        for row in self.env.cr.fetchall():
            if row[1] != "v":
                query += """
                    DROP TABLE %s;
                """ % row[0]

        self.env.cr.execute(query + """
            CREATE or REPLACE VIEW product_tag_stock_valuation_layer_rel AS (
                SELECT svl.id AS stock_valuation_layer_id, pr.product_tag_id
                FROM stock_valuation_layer svl 
                JOIN product_product pp ON pp.id = svl.product_id 
                JOIN product_template pt ON pp.product_tmpl_id = pt.id 
                JOIN product_tag_product_template_rel pr ON pr.product_template_id = pt.id
            );
            
            CREATE or REPLACE VIEW product_tag_stock_quant_rel AS (
                SELECT sq.id AS stock_quant_id, pr.product_tag_id
                FROM stock_quant sq 
                JOIN product_product pp ON pp.id = sq.product_id 
                JOIN product_template pt ON pp.product_tmpl_id = pt.id 
                JOIN product_tag_product_template_rel pr ON pr.product_template_id = pt.id
            );
            
            CREATE or REPLACE VIEW product_tag_account_move_line_rel AS (
                SELECT aml.id AS account_move_line_id, pr.product_tag_id
                FROM account_move_line aml
                JOIN product_product pp ON pp.id = aml.product_id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                JOIN product_tag_product_template_rel pr ON pr.product_template_id = pt.id
            );
        """)
