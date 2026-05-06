from odoo import fields, models

class HrContract(models.Model):
    _inherit = 'hr.contract'

    wage_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('hourly', 'Hourly')
    ], string='Wage Type', default='monthly', required=True,
    help="Specifies whether the wage is paid monthly or hourly.")
