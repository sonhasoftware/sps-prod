# -*- coding: utf-8 -*-
{
    'name': "HR Recruitment customize",
    'description': """
        HR Recruitment customize
    """,
    'author': "THG",
    'website': "http://thg.net",
    'version': '0.1',
    'depends': ['hr_recruitment', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/hr_recruit_request.xml',
        'views/hr_applicant.xml',
        'reports/candidates_report.xml',
        'reports/inquiry_position_report.xml',

        'data/ir_cron.xml',
    ],
}
