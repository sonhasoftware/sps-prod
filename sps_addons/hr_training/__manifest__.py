# -*- coding: utf-8 -*-
{
    'name': "HR Training",
    'description': """
        HR Training
    """,
    'author': "THG",
    'website': "http://thg.net",
    'version': '0.1.1',
    'depends': ['hr', 'project'],
    'external_dependencies': {'python': [
        'docxtpl',
    ]},
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/views.xml',
        'views/hr_training.xml',
        'views/hr_job.xml',
        'views/hr_employee_training_out.xml',
        'wizards/training_monthly_report.xml',
        'report/report_monthly.xml',
        'report/report_trainers.xml',
        'report/report_training_standard.xml',
        'report/report_missingitem.xml',
    ],
}
