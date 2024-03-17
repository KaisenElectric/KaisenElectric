{
    "name": "Kaisen FX Adjustment Automation",
    "summary": """Модуль автоматизации коррекции курсов: программное обеспечение для автоматического создания и отмены бухгалтерских проводок по курсовым разницам в соответствии с предварительно заданным расписанием.""",
    "description": """
    Модуль автоматизации коррекции курсов представляет собой интегрированную систему, разработанную
    для оптимизации процесса учета валютных операций. Он автоматически создает бухгалтерские проводки
    на основе заданного расписания коррекций курсов и обеспечивает отмену этих проводок на следующий день.
    Это позволяет обеспечить точность и надежность данных в отчетах по валютным счетам, снизить ручное
    вмешательство и минимизировать риски ошибок.
    """,
    "author": "Kaisen",
    'category': 'Accounting/Accounting',
    "version": "15.0.0.1",
    "license": "Other proprietary",
    "depends": [
        "account",
        "kaisen_base_upgrade",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/cron.xml",
        "views/kaisen_schedule_fx_adjustment_views.xml",
        "views/kaisen_schedule_fx_adjustment_log_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {},
    "qweb": [],
    "application": True,
}
