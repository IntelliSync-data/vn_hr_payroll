# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

class VnPayrollSalaryRule(models.Model):
    _name = 'vnpayroll.salary.rule'
    _description = 'VN Payroll Salary Rule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, code'

    name = fields.Char(string='Name', required=True, tracking=True)
    code = fields.Char(string='Code', required=True, tracking=True)
    sequence = fields.Integer(default=5, help="Use to arrange calculation sequence", tracking=True)
    active = fields.Boolean(default=True, help="If the active field is set to false, it will allow you to hide the salary rule without removing it.")
    appears_on_payslip = fields.Boolean(string="Appears on Payslip", default=True, help="Used to display the salary rule on payslip.")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)
    
    category_id = fields.Many2one('vnpayroll.salary.rule.category', string='Category', required=True, tracking=True)
    struct_id = fields.Many2one('vnpayroll.payroll.structure', string='Salary Structure', tracking=True, ondelete='cascade')

    condition_select = fields.Selection([
        ('none', 'Always True'),
        ('range', 'Range'),
        ('python', 'Python Expression')
    ], string='Condition Based on', default='none', required=True)
    condition_range_min = fields.Float(string='Range Minimum', help="The minimum value for the range condition")
    condition_range_max = fields.Float(string='Range Maximum', help="The maximum value for the range condition")
    condition_range = fields.Char(string='Range Based on', help="The code that will be executed to get the value to compare to the range.")
    condition_python = fields.Text(string='Python Condition', 
                                   default='''
# Available variables:
#----------------------
# payslip: object containing the payslips
# employee: hr.employee object
# contract: hr.contract object
# rules: object containing the rules code (previously computed)
# categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category)
# worked_days: object containing the computed worked days
# inputs: object containing the computed inputs.

# Note: returned value have to be set in the variable 'result'

result = True
''')

    amount_select = fields.Selection([
        ('fix', 'Fixed Amount'),
        ('percentage', 'Percentage (%)'),
        ('python', 'Python Code')
    ], string='Amount Type', default='fix', required=True, index=True)
    amount_fix = fields.Float(string='Fixed Amount')
    amount_percentage = fields.Float(string='Percentage (%)', help='For Percentage amount type')
    amount_percentage_base = fields.Char(string='Percentage based on', help='The python code that will be executed to get the value on which the percentage will be applied.')
    amount_python_compute = fields.Text(string='Python Code',
                                        default='''
# Available variables:
#----------------------
# payslip: object containing the payslips
# employee: hr.employee object
# contract: hr.contract object
# rules: object containing the rules code (previously computed)
# categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category)
# worked_days: object containing the computed worked days
# inputs: object containing the computed inputs.

# Note: returned value have to be set in the variable 'result'

result = contract.wage * 0.10
''')

    partner_id = fields.Many2one('res.partner', string='Partner', help="Partner for this salary rule, if applicable.")
    note = fields.Text(string='Description')

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)', 'The code of the salary rule must be unique per company!'),
        ('name_company_uniq', 'unique(name, company_id)', 'The name of the salary rule must be unique per company!'),
    ]

    @api.constrains('condition_range_min', 'condition_range_max')
    def _check_condition_range(self):
        for rule in self:
            if rule.condition_select == 'range' and rule.condition_range_min > rule.condition_range_max:
                raise ValidationError("The minimum for the range condition cannot be greater than the maximum.")

    def _satisfy_condition(self, localdict):
        self.ensure_one()
        if self.condition_select == 'none':
            return True
        if self.condition_select == 'range':
            try:
                result = safe_eval(self.condition_range, localdict)
                return self.condition_range_min <= result <= self.condition_range_max
            except Exception as e:
                raise UserError(f'Wrong range condition defined for salary rule {self.name} ({self.code}).\nError: {e}')
        else:  # python code
            try:
                safe_eval(self.condition_python, localdict, mode='exec', nocopy=True)
                return localdict.get('result', False)
            except Exception as e:
                raise UserError(f'Wrong python condition defined for salary rule {self.name} ({self.code}).\nError: {e}')

    def _compute_rule(self, localdict):
        self.ensure_one()
        if not self._satisfy_condition(localdict):
            return 0.0, False # amount, is_applicable

        if self.amount_select == 'fix':
            return self.amount_fix, True
        elif self.amount_select == 'percentage':
            try:
                percentage_base = safe_eval(self.amount_percentage_base, localdict)
                return (percentage_base * self.amount_percentage) / 100.0, True
            except Exception as e:
                raise UserError(f'Wrong percentage base or value defined for salary rule {self.name} ({self.code}).\nError: {e}')
        else:  # python code
            try:
                safe_eval(self.amount_python_compute, localdict, mode='exec', nocopy=True)
                return float(localdict.get('result', 0.0)), True
            except Exception as e:
                raise UserError(f'Wrong python code defined for salary rule {self.name} ({self.code}).\nError: {e}')

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.name} ({record.code})"
