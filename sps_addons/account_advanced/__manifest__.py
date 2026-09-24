# -*- coding: utf-8 -*-
{
    'name': "Account_Advanced",

    'summary': """
        Chức năng mới tạm ứng hoàn ứng""",

    'description': """
        Chức năng mới tạm ứng hoàn ứng
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
                'hr',
                'uom',
                'account_accountant',
                'xpurchase',
                'account',
                'sps_sale_target'],

    # always loaded
    'data': [
        'security/group.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/code_money_view.xml',
        'views/account_advance_view.xml',
        'views/account_repay.xml',
        'views/purchase_order.xml',
        'reports/advanced_repay_report.xml',
        'reports/advanced_report.xml',
    ],
    # only loaded in demonstration mode
    'auto_install': False,
    'application': False,
}
