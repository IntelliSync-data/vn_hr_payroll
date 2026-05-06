# -*- coding: utf-8 -*-
from odoo import models, fields, api

class VnPayrollSalaryRuleCategory(models.Model):
    _name = 'vnpayroll.salary.rule.category'
    _description = 'VN Payroll Salary Rule Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, code'

    name = fields.Char(string='Name', required=True, tracking=True)
    code = fields.Char(string='Code', required=True, tracking=True)
    sequence = fields.Integer(default=5, help="Sequence for ordering categories.", tracking=True)
    parent_id = fields.Many2one(
        'vnpayroll.salary.rule.category', 
        string='Parent Category', 
        index=True, 
        ondelete='cascade',
        tracking=True
    )
    children_ids = fields.One2many(
        'vnpayroll.salary.rule.category', 
        'parent_id', 
        string='Child Categories',
        tracking=True
    )
    note = fields.Text(string='Description')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)', 'The code of the salary rule category must be unique per company!'),
        ('name_company_uniq', 'unique(name, company_id)', 'The name of the salary rule category must be unique per company!'),
    ]

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.name} ({record.code})"
