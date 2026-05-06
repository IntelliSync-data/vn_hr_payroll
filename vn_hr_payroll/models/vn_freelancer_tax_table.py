from odoo import models, fields, api


class VnFreelancerTaxTable(models.Model):
    _name = 'vn.freelancer.tax.table'
    _description = 'Vietnam Freelancer Tax Table'
    _order = 'income_from'

    name = fields.Char(string='Name', required=True)
    income_from = fields.Float(string='Income From', required=True)
    income_to = fields.Float(string='Income To', required=True)
    tax_rate = fields.Float(string='Tax Rate (%)', required=True)
    fixed_deduction = fields.Float(string='Fixed Deduction', required=True, default=0.0)
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.constrains('income_from', 'income_to')
    def _check_income_range(self):
        for record in self:
            if record.income_from >= record.income_to:
                raise models.ValidationError('Income From must be less than Income To')
