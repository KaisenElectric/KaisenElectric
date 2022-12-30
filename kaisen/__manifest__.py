{
    "name": "Kaisen",
    "summary": """Kaisen""",
    "description": """Kaisen""",
    "author": "ICode",
    "website": "https://icode.by/",
    "category": "Uncategorized",
    "version": "15.0.1",
    "license": "Other proprietary",
    "depends": [
        "purchase",
        "stock",
        "purchase_stock",
        "product",
        "base_address_extended",
        "account_sequence_option",
        "sale",
        "delivery",
    ],
    "data": [
        # SECURITY
        # DATA
        # VIEWS
        "views/stock_picking_views.xml",
        "views/res_config_settings_views.xml",
        "views/product_packaging.xml",
        "views/stock_quant.xml",
        "views/purchase_order_views.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "views/delivery_carrier_views.xml",
        "views/stock_move_line_views.xml",
        # WIZARDS
        # REPORTS
    ],
    "qweb": [],
    "application": True,
}
