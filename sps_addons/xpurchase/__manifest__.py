# -*- coding: utf-8 -*-
{
    'name': 'SPS Purchase',
    'version': '14.0.0.1.0',
    'description': '',
    'author': 'THG',
    'website': '',
    'license': 'OPL-1',
    'category': 'Services/Project',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'hr',
                'uom',
                'product',
                'sale',
                'stock',
                'account_accountant',
                'purchase',
                'account',
                'sps_sale_target',
                'web'],


    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/cost_type.xml',
        'views/request_purchase_sonvt.xml',
        'views/purchase_order.xml',
        'data/purchase_number_code.xml',
        'views/res_partner_action_supplier_view.xml',
        'views/product_junk_view.xml',
        'views/category_list_view.xml',
        'wizards/purchase_report.xml',
        'wizards/purchase_quotation_report.xml',
        'wizards/change_requisition_qty.xml',
        'reports/template.xml',
        'views/assets.xml',

    ],
 }
