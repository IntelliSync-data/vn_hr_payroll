# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class VnPitTaxTable(models.Model):
    _name = 'vn.pit.tax.table'
    _description = 'Vietnam Personal Income Tax Table'
    _order = 'income_from asc'
    
    name = fields.Char(string='Name', compute='_compute_name', store=True)
    income_from = fields.Float(string='Income From', required=True,
                             help='Starting income amount for this tax bracket')
    income_to = fields.Float(string='Income To', required=True,
                           help='Ending income amount for this tax bracket')
    tax_rate = fields.Float(string='Tax Rate (%)', required=True,
                          help='Tax rate percentage for this bracket')
    fixed_deduction = fields.Float(string='Fixed Deduction', required=True,
                                 help='Fixed deduction amount for this bracket')
    
    @api.depends('income_from', 'income_to', 'tax_rate')
    def _compute_name(self):
        for record in self:
            if record.income_to < float('inf'):
                record.name = f'{int(record.income_from):,} - {int(record.income_to):,} ({record.tax_rate}%)'
            else:
                record.name = f'Over {int(record.income_from):,} ({record.tax_rate}%)'
    
    @api.constrains('income_from', 'income_to')
    def _check_income_range(self):
        for record in self:
            if record.income_from >= record.income_to and record.income_to < float('inf'):
                raise ValidationError(_('Income From must be less than Income To'))
            
            # Check for overlapping ranges (dùng strict overlap, không tính liền kề)
            overlaps = self.search([
                ('id', '!=', record.id),
                '|',
                '&', ('income_from', '<', record.income_to), ('income_to', '>', record.income_from),
                '&', ('income_from', '<', record.income_to), ('income_to', '>', record.income_from),
            ])
            # Lọc thêm - chỉ overlap thật sự (không tính trường hợp liền kề như 5M-5M)
            real_overlaps = overlaps.filtered(
                lambda r: r.income_from < record.income_to and r.income_to > record.income_from
                and not (r.income_to == record.income_from or r.income_from == record.income_to)
            )
            if real_overlaps:
                raise ValidationError(_('Tax brackets cannot overlap with existing brackets'))
    
    @api.constrains('tax_rate')
    def _check_tax_rate(self):
        for record in self:
            if record.tax_rate < 0 or record.tax_rate > 100:
                raise ValidationError(_('Tax rate must be between 0 and 100'))
    
    @api.model
    def calculate_tax(self, income):
        """Calculate tax amount based on progressive tax table"""
        if income <= 0:
            return 0
            
        tax_brackets = self.search([], order='income_from asc')
        if not tax_brackets:
            return 0
            
        for bracket in tax_brackets:
            if income <= bracket.income_to:
                return income * bracket.tax_rate / 100 - bracket.fixed_deduction
                
        # If income exceeds all brackets, use the highest bracket
        highest_bracket = tax_brackets[-1]
        return income * highest_bracket.tax_rate / 100 - highest_bracket.fixed_deduction
