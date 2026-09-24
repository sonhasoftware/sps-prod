# -*- coding: utf-8 -*-
{
    'name': "Payroll customize",
    'description': """
        Payroll customize
    """,
    'author': "THG",
    'website': "http://thg.net",
    'version': '0.1.8',
    'depends': ['hr_holidays', 'hr_payroll', 'hr_holidays', 'hr_work_entry', 'project', 'resource', 'hr_work_entry_contract', 'hr_work_entry_holidays'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/config_data.xml',
        'data/ir_cron.xml',
        'views/views.xml',
        'views/hr_views.xml',
        'views/payroll_views.xml',
        'views/leave_views.xml',
        'views/hr_work_entry_views.xml',
        'views/hr_work_factor_views.xml',
        'views/hr_work_shift_views.xml',
        'views/hr_global_off_views.xml',
        'views/wage_cost_actual.xml',
        'views/payslip_run.xml',
        'views/kpi_evaluation.xml',
        'views/meal_rate_views.xml',
        'report/report_payslip_templates.xml',
        'wizard/payroll_mixin_config.xml',
        'wizard/report_payslip_approve_views.xml',
        'wizard/report_payslip_approve_with_bank_account_views.xml',
        'wizard/report_payslip_year_views.xml',
        'wizard/report_payslip_salary_views.xml',
        'wizard/report_payslip_travel_views.xml',
        'wizard/report_payslip_balance_views.xml',
        'wizard/report_payslip_advance_views.xml',
        'wizard/report_payslip_imprest_views.xml',
        'wizard/report_payslip_gasoline_views.xml'
    ],
}

