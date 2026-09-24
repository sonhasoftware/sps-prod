# -*- coding: utf-8 -*-
{
    'name': "SPS Stock",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "THG",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '14.0.0.2.4',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'hr',
        'uom',
        'product',
        'product_expiry',
        'sale',
        'stock',
        'account_accountant',
        'purchase',
        'sps_sale_target',
        'xproject',
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_view.xml',
        'views/stock_borrow_tools_view.xml',
        'views/stock_location_views.xml',
        'views/stock_inventory_view.xml',
        'views/stock_production_lot_view.xml',
        'views/product_template.xml',
        'wizards/stock_list_report.xml',
        'wizards/stock_supplies_report.xml',
        'wizards/stock_inventory_tools.xml',
        'wizards/stock_report_cost.xml',
        'wizards/employee_damage_value_popup.xml',
        'wizards/employee_tools_value_popup.xml',
        'wizards/stock_report_detail_popup_clone.xml',
        'wizards/stock_report_detail_popup_wizard.xml',
        'wizards/ccdc_usage_report.xml',

        'reports/employee_tools_value_report.xml',
        'reports/employee_damage_value_report.xml',
        'reports/stock_report_cost.xml',
        'reports/stock_supplies_rp.xml',
    ],
}
