{
    "name": "Kaisen Recipient bank",
    "summary": """Adds the Recipient bank field""",
    "description": """Adds the beneficiary bank field to the client card and fills in the beneficiary bank field in the Sale Order when the partner changes""",
    "author": "Kaisen",
    'category': 'Accounting/Accounting',
    "version": "15.0.0.0.1",
    "license": "Other proprietary",
    "depends": [
        "account",
        "kaisen",
    ],
    "data": [
        "views/res_partner_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
        ],
    },
    "qweb": [],
    "application": True,
}
