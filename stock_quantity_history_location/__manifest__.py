{
    "name": "Stock Quantity History Location",
    "summary": "Provides stock quantity by location on past date",
    "version": "15.0.1.0.0",
    "author": "Icode",
    "depends": ["stock"],
    "assets": {
        "web.assets_backend": [
            "stock_quantity_history_location/static/src/js/inventory_report.js",
        ],
    },
    "data": [
        "wizards/stock_quantity_history.xml",
    ],
}
