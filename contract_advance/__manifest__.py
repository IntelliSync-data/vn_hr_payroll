{
    'name': 'Contract Extension (Hourly/Monthly)',
    'version': '18.0.1.0.0',
    'category': 'ISD Modules',
    'summary': 'Extends contracts to support hourly and monthly wages.',
    'description': """
        This module extends the Odoo Contract functionality to:
        - Differentiate between monthly and hourly wage types on the contract.
    """,
    'author': 'Cascade AI',
    'website': 'https://intellisyncdata.com',
    'depends': ['hr_contract'],
    'data': [
        'views/hr_contract_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
