# -*- coding: utf-8 -*-
{
    'name': "Account_saving",

    'summary': """
        Chức năng mới Tiền gửi tiết kiệm""",

    'description': """
        Chức năng mới tiền gửi tiết kiệm
    """,

    'author': "THG",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'xbase',
                'account_accountant',
                'account',
                'report_xlsx',
                'account_advanced'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/cash_flow_code_mapping_data.xml',
        'views/account_saving_views.xml',
        'views/cash_flow_report_detail_views.xml',
        'views/cash_flow_code_mapping_views.xml',
        'views/web_assets.xml',
        'reports/cash_flow_report.xml',
        'wizards/savings_deposit_report.xml',
        'wizards/cash_flow_report.xml',
        'wizards/cash_flow_preview_wizard.xml',
        'wizards/cash_report.xml',
        'wizards/report_debt.xml',
        'wizards/turn_over_report.xml',
        'wizards/detail_debit.xml',
        'wizards/internal_fund.xml',
        'reports/savings_deposit_report.xml',
        'reports/payment_order.xml',
        'reports/print_advance_repay.xml',
        'reports/cash_report.xml',
        'reports/report_debt.xml',
        'reports/detail_debit.xml',
        'reports/cash_report.xml',
                ],
    # only loaded in demonstration mode
    'auto_install': False,
    'application': False,
}
