# -*- coding: utf-8 -*-
{
    'name': "HR customize",
    'description': """
        HR customize
    """,
    'author': "THG",
    'website': "http://thg.net",
    'version': '14.0.0.3.0',
    'depends': ['hr', 'hr_contract', 'project', 'resource'],
    'external_dependencies': {'python': [
        'docxtpl',
    ]},
    'data': [
        'security/ir.model.access.csv',
        'security/hr_security.xml',
        'data/data.xml',
        'views/hr.xml',
        'report/classification.xml',
        'views/hr_employee_ethnic.xml',
    ],
}
