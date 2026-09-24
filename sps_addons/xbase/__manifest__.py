# -*- coding: utf-8 -*-
{
    'name': "Base customize",
    'description': """
        Base customize
    """,
    'author': "THG",
    'website': "http://thg.net",
    'version': '0.1',
    'depends': ['web', 'mail','base'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/templates.xml',
        'data/translation_cron.xml',
        'views/res_users_views.xml',
    ],
    'auto_install': True,
}
