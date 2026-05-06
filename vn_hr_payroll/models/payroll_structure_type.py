# -*- coding: utf-8 -*-
from odoo import models, fields, api

class VnPayrollStructureType(models.Model):
    _name = 'vnpayroll.payroll.structure.type'
    _description = 'VN Payroll Structure Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    
    name = fields.Char(string='Name', required=True, tracking=True)
    code = fields.Char(string='Code', required=True, tracking=True)
    country_id = fields.Many2one('res.country', string='Country', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    default_resource_calendar_id = fields.Many2one('resource.calendar', string='Default Working Hours')
    
    default_struct_id = fields.Many2one(
        'vnpayroll.payroll.structure', 
        string='Default Salary Structure',
        help="Default salary structure used for new contracts.", 
        tracking=True
    )
    struct_ids = fields.One2many(
        'vnpayroll.payroll.structure', 
        'type_id',
        string='Salary Structures', 
        tracking=True
    )

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'The name of the payroll structure type must be unique per company!'),
        ('code_company_uniq', 'unique(code, company_id)', 'The code of the payroll structure type must be unique per company!'),
    ]

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.name} ({record.code if record.code else ''})"
