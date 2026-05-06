# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HrContract(models.Model):
    _inherit = 'hr.contract'
    
    # Thay vì ghi đè trường structure_type_id, chúng ta sẽ sử dụng trường mới
    vn_structure_type_id = fields.Many2one('vnpayroll.payroll.structure.type', string='VN Salary Structure Type')
    
    # Override default _compute_structure_type_id để tương thích với module vn_hr_payroll
    @api.depends('company_id')
    def _compute_structure_type_id(self):
        for contract in self:
            # Nếu đã có vn_structure_type_id, sử dụng giá trị mặc định
            if contract.vn_structure_type_id:
                # Không thay đổi structure_type_id nếu đã được thiết lập
                continue
            else:
                # Gọi phương thức gốc
                super(HrContract, contract)._compute_structure_type_id()
    
    # Vietnamese Payroll specific fields
    vn_basic_wage = fields.Float(string='Basic Wage', default=0.0,
                               help='Basic wage amount in VND')
    vn_allowances = fields.Float(string='Allowances', default=0.0,
                               help='Total allowances amount in VND')
    vn_insurance_wage = fields.Float(string='Insurance Wage', default=0.0,
                                   help='Wage used for insurance contribution calculation')
    vn_personal_deduction = fields.Float(string='Personal Deduction', default=11000000,
                                       help='Personal tax deduction amount in VND')
    vn_dependant_deduction = fields.Float(string='Dependant Deduction', default=4400000,
                                        help='Deduction amount per dependant in VND')
    vn_number_of_dependants = fields.Integer(string='Number of Dependants', default=0,
                                           help='Number of dependants for tax calculation')
    vn_union_fee = fields.Float(string='Union Fee', default=0.0,
                              help='Union fee amount in VND')
    
    # Computed fields
    vn_total_dependant_deduction = fields.Float(string='Total Dependant Deduction', 
                                              compute='_compute_vn_deductions',
                                              help='Total deduction for all dependants')
    vn_total_deduction = fields.Float(string='Total Deduction', 
                                    compute='_compute_vn_deductions',
                                    help='Total deduction including personal and dependants')
    
    @api.depends('vn_personal_deduction', 'vn_dependant_deduction', 'vn_number_of_dependants')
    def _compute_vn_deductions(self):
        for contract in self:
            contract.vn_total_dependant_deduction = contract.vn_dependant_deduction * contract.vn_number_of_dependants
            contract.vn_total_deduction = contract.vn_personal_deduction + contract.vn_total_dependant_deduction
    
    @api.onchange('wage')
    def _onchange_wage(self):
        if self.wage:
            # Default values if not set
            if not self.vn_basic_wage:
                self.vn_basic_wage = self.wage
            if not self.vn_insurance_wage:
                self.vn_insurance_wage = self.wage
    
    @api.constrains('vn_number_of_dependants')
    def _check_vn_number_of_dependants(self):
        for contract in self:
            if contract.vn_number_of_dependants < 0:
                raise ValidationError(_('Number of dependants cannot be negative.'))
