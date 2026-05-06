# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class VnPayrollStructure(models.Model):
    _name = 'vnpayroll.payroll.structure'
    _description = 'VN Payroll Structure'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Name', required=True, tracking=True)
    code = fields.Char(string='Code', required=True, tracking=True)
    active = fields.Boolean(default=True, help="If the active field is set to false, it will allow you to hide the salary structure without removing it.")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True, tracking=True)
    type_id = fields.Many2one('vnpayroll.payroll.structure.type', string='Type', required=True, tracking=True)
    parent_id = fields.Many2one('vnpayroll.payroll.structure', string='Parent Structure', tracking=True, help="Salary structure from which this structure inherits rules.")
    rule_ids = fields.Many2many(
        'vnpayroll.salary.rule', 
        'vnpayroll_structure_salary_rule_rel', 
        'struct_id', 
        'rule_id', 
        string='Salary Rules', 
        tracking=True
    )
    note = fields.Text(string='Description')
    payslip_name = fields.Char(string='Payslip Name', help="Name to be used for payslips generated from this structure.")
    schedule_pay = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi-annually', 'Semi-annually'),
        ('annually', 'Annually'),
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-weekly'),
        ('bi-monthly', 'Bi-monthly'),
    ], string='Scheduled Pay', index=True, default='monthly', help="Defines the frequency of pay slips.")

    _sql_constraints = [
        ('code_company_uniq', 'unique (code, company_id)', 'The code of the salary structure must be unique per company!'),
        ('name_company_uniq', 'unique (name, company_id)', 'The name of the salary structure must be unique per company!'),
    ]

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError('Error! You cannot create recursive salary structures.')

    def _check_recursion(self, parent=None):
        #Keeps track of parents encountered to detect recursions
        if parent is None:
            parent = {}
        #Traveses the hierarchy of structures, returning False if a recursion is detected
        #The parent parameter is a dictionary whose key is the structure id and the value is the parent id
        #The first call has to be done with parent=None
        for structure in self:
            #If the structure is already in the dict, it means it has already been checked
            if structure.id in parent:
                continue
            parent[structure.id] = structure.parent_id.id
            if structure.parent_id.id in parent and structure.parent_id.id == parent[structure.parent_id.id]:
                #Recursion detected
                return False
            if structure.parent_id and not structure.parent_id._check_recursion(parent=parent):
                return False
        return True

    def get_all_rules(self):
        """ Returns a list of tuple (id, sequence) of rules that are present in the structure
        and all of its parents. """
        all_rules = []
        for struct in self:
            all_rules += struct.rule_ids.sorted(key=lambda r: r.sequence).ids
            if struct.parent_id:
                all_rules += struct.parent_id.get_all_rules()
        return list(set(all_rules)) # Use set to remove duplicates, then convert to list

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.name} ({record.code if record.code else ''})"
