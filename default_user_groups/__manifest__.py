# -*- coding: utf-8 -*-
{
    'license': 'LGPL-3',
    'name': 'Default User Groups',
    'version': '18.0.1.0.0',
    'summary': 'Automatically assign default groups to new users',
    'author': 'IntelliSyncData',
    'website': 'https://intellisyncdata.com',
    'support': 'info@intellisyncdata.com',
    'category': 'ISD Modules',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/default_groups_config_views.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}