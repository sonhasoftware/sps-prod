# -*- coding: utf-8 -*-
{
    'name': "Effective_Management",

    'summary': """ QUản lý hiệu quả """,

    'description': """
        Chứa các báo cáo thể hiện hiệu quả các bộ phận của công ty
    """,

    'author': "THG",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['xbase',
                'xstock',
                'xaccount',
                'xpurchase',
                'sps_sale_target',
                'xproject','xhr','xhr_payroll','account_saving'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/effective_menu.xml',

        # purchase
        'views/purchase/purchase_picking_status.xml',
        'views/purchase/purchase_picking_requesters.xml',
        'views/purchase/purchase_payment_value.xml',
        'views/purchase/purchase_tracking_supplier.xml',
        'views/purchase/purchase_compare_effective.xml',

        # wizard purchase
        'wizards/purchase/purchase_picking_status_wizards.xml',
        'wizards/purchase/purchase_payment_value_wizards.xml',
        'wizards/purchase/purchase_tracking_supplier_wizards.xml',
        'wizards/purchase/purchase_compare_effective_wizards.xml',

        #hr
        'views/recruitment/recruitment_efficiency_report.xml',
        'views/recruitment/recruitment_report_monthly.xml',
        #hr_wizards
        'wizards/recruitment/recruitment_efficiency_wizards.xml',
        'wizards/recruitment/recruitment_monthly_wizards.xml',
        #sale
        'views/sale/sale_volume.xml',
        'views/sale/sale_quantity.xml',
        'views/sale/sale_analysis.xml',
        'views/sale/sale_key_account.xml',
        'views/sale/sale_signed_incentive.xml',
        'views/sale/sale_closed_incentive.xml',
        'views/sale/sale_annual.xml',
        #sale wizard
        'wizards/sale/sale_volume_wizards.xml',
        'wizards/sale/sale_quantity_wizards.xml',
        'wizards/sale/sale_analysis_wizards.xml',
        'wizards/sale/sale_key_account_wizards.xml',
        'wizards/sale/sale_signed_incentive_wizards.xml',
        'wizards/sale/sale_closed_incentive_wizards.xml',
        'wizards/sale/sale_annual_wizards.xml',
        #project
        'views/project/project_efficiency_coefficient.xml',
        'views/project/project_manager_labor_cost.xml',
        'views/project/project_non_labor_cost.xml',
        'views/project/project_sum_value_labor.xml',
        'views/project/project_efficiency_detail.xml',
        'views/project/project_reward_detail.xml',
        'views/project/group_project_efficiency_detail.xml',
        #project wizard
        'wizards/project/project_efficiency_coefficient_wizards.xml',
        'wizards/project/project_non_labor_cost_wizards.xml',
        'wizards/project/project_manager_labor_cost_wizards.xml',
        'wizards/project/project_sum_value_labor_wizards.xml',
        'wizards/project/project_efficiency_detail_wizards.xml',
        'wizards/project/project_reward_detail_wizards.xml',
        'wizards/project/group_project_efficiency_detail_wizards.xml',
        #employee
        'views/employee/employee_effective.xml',
        'views/employee/annual_labor_productivity_target_views.xml',
        'wizards/employee/employee_effective_wizards.xml',

    ],
    # only loaded in demonstration mode
    'auto_install': False,
    'application': False,
}
