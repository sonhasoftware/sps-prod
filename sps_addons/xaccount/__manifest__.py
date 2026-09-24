# -*- coding: utf-8 -*-
{
    'name': "SPS_Account",

    'summary': """
        Phân hệ kế toán custom by THG""",

    'description': """
        Phân hệ kế toán custom by THG
    """,

    'author': "THG",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.3',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'hr',
        'uom',
        'account_accountant',
        'purchase',
        'account',
        'sps_sale_target',
        'account_advanced',
        'account_reports',
        'xproject'
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizards/sale_payment_deposit.xml',
        'views/views.xml',
        'views/deposit_tracking.xml',
        'views/account_payment.xml',
        'views/account_move.xml',
        'views/sale_order.xml',
        'views/tndn_tax_rate.xml',
        'views/purchase_order.xml',
        'views/account_menu.xml',
        'views/account_move_line.xml',
        'views/account_hide_menu.xml',
        'reports/template.xml',

        'data/ir_sequence.xml',
    ],

}
