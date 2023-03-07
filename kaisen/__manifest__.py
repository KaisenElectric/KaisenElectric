{
    "name": "Kaisen",
    "summary": """Kaisen""",
    "description": """Kaisen""",
    "author": "ICode",
    "website": "https://icode.by/",
    "category": "Uncategorized",
    "version": "15.0.1.0.1",
    "license": "Other proprietary",
    "depends": [
        "base",
        "web",
        "purchase",
        "account",
        "stock",
        "purchase_stock",
        "product",
        "base_address_extended",
        "account_sequence_option",
        "sale",
        "delivery",
        "web_widget_dropdown_dynamic",
        "sale_margin",
        "account_inter_company_rules",
        "stock_landed_costs",
        "stock_account",
    ],
    "data": [
        # SECURITY
        "security/kaisen_security.xml",
        "security/ir.model.access.csv",
        # DATA
        "data/external_integration_data.xml",
        # VIEWS
        "views/stock_picking_views.xml",
        "views/res_config_settings_views.xml",
        "views/product_packaging_views.xml",
        "views/stock_quant_views.xml",
        "views/purchase_order_views.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "views/delivery_carrier_views.xml",
        "views/stock_move_line_views.xml",
        "views/external_integration_views.xml",
        "views/stock_quant_package_views.xml",
        "views/res_company_views.xml",
        "views/res_partner_views.xml",
        "views/stock_valuation_layer_views.xml",
        "views/account_tax_views.xml",
        # WIZARDS
        "wizards/import_of_cost_of_products_wizard_views.xml",
        # REPORTS
        "views/menus.xml",
        "reports/sale_report_templates.xml",
    ],
    "qweb": [],
    "application": True,
}
