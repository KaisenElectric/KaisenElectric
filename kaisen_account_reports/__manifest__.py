{
    "name": "Kaisen Account Reports",
    "summary": """Customization Account Reports""",
    "description": """
        Adds option exclude partners.
    """,
    "author": "Kaisen",
    'category': 'Accounting/Accounting',
    "version": "15.0.0.0.3",
    "license": "Other proprietary",
    "depends": [
        "account_reports",
    ],
    "data": [
        "views/search_template_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            'kaisen_account_reports/static/src/js/m2m_filters.js',
            'kaisen_account_reports/static/src/js/account_reports.js',
        ],
    },
    "qweb": [],
    "application": True,
}
