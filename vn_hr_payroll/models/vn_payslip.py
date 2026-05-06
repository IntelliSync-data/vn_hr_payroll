# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import base64
import logging
import io
import string
import random

_logger = logging.getLogger(__name__)

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    _logger.warning('pypdf library not found. PDF encryption will be disabled.')
    PdfReader = PdfWriter = None

class VnPayslip(models.Model):
    _name = 'vn.payslip'
    _description = 'Vietnam Payslip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, id desc'
    
    name = fields.Char(string='Name', required=True, default=lambda self: _('New Payslip'))
    
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    
    contract_id = fields.Many2one('hr.contract', string='Contract', required=True,
                                 domain="[('employee_id', '=', employee_id), ('state', '=', 'open')]",
                                 ondelete='cascade')

    schedule_id = fields.Many2one('vn.payslip.schedule', string='Schedule', ondelete='set null',
                                  help='Payslip Schedule that generated this payslip')

    is_freelancer = fields.Boolean(string='Is Freelancer', compute='_compute_is_freelancer', store=True)
    is_hourly = fields.Boolean(string='Is Hourly', compute='_compute_is_hourly', store=True)

    @api.depends('contract_id', 'contract_id.vn_structure_type_id')
    def _compute_is_freelancer(self):
        for payslip in self:
            if payslip.contract_id and payslip.contract_id.vn_structure_type_id:
                payslip.is_freelancer = payslip.contract_id.vn_structure_type_id.name == 'Freelancer/Contractor'
            else:
                payslip.is_freelancer = False

    @api.depends('contract_id', 'contract_id.vn_structure_type_id')
    def _compute_is_hourly(self):
        for payslip in self:
            if payslip.contract_id and payslip.contract_id.vn_structure_type_id:
                structure_name = payslip.contract_id.vn_structure_type_id.name
                payslip.is_hourly = structure_name in ['Freelancer/Contractor', 'Hourly'] or 'Hourly' in structure_name
            else:
                payslip.is_hourly = False
    
    date_from = fields.Date(string='Date From', required=True,
                           default=lambda self: fields.Date.today().replace(day=1))
    
    date_to = fields.Date(string='Date To', required=True,
                        default=lambda self: fields.Date.from_string(fields.Date.end_of(fields.Date.today(), 'month')))
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('cancel', 'Rejected')
    ], string='Status', index=True, readonly=True, copy=False, default='draft',
        help="""* When the payslip is created the status is 'Draft'
                \n* If the payslip is under verification, the status is 'Waiting'
                \n* If the payslip is confirmed then status is set to 'Done'
                \n* When user cancel payslip the status is 'Rejected'""")
    
    # Wage fields
    basic_wage = fields.Float(string='Basic Wage')
    allowances = fields.Float(string='Allowances')
    gross_wage = fields.Float(string='Gross Wage')

    # Time Off fields (for monthly wage calculation)
    total_working_days = fields.Float(string='Total Working Days', compute='_compute_time_off_data', store=True,
                                       help='Total working days in period (Mon-Fri only)')
    pto_days = fields.Float(string='Paid Time Off Days', compute='_compute_time_off_data', store=True,
                            help='Number of paid leave days (Ngày nghỉ có lương)')
    unpaid_leave_days = fields.Float(string='Unpaid Leave Days', compute='_compute_time_off_data', store=True,
                                      help='Number of unpaid leave days (Nghỉ không lương)')
    actual_working_days = fields.Float(string='Actual Working Days', compute='_compute_time_off_data', store=True,
                                        help='Actual days worked (Total - PTO - Unpaid)')
    paid_working_days = fields.Float(string='Paid Working Days', compute='_compute_time_off_data', store=True,
                                      help='Days used for salary calculation (Actual + PTO)')
    
    # Freelancer specific fields
    worked_hours = fields.Float(string='Worked Hours', default=0.0,
                              help='Number of hours worked by the freelancer')
    
    # Insurance fields
    si_employee = fields.Float(string='SI (Employee)', compute='_compute_insurances', store=True)
    hi_employee = fields.Float(string='HI (Employee)', compute='_compute_insurances', store=True)
    ui_employee = fields.Float(string='UI (Employee)', compute='_compute_insurances', store=True)
    si_company = fields.Float(string='SI (Company)', compute='_compute_insurances', store=True)
    hi_company = fields.Float(string='HI (Company)', compute='_compute_insurances', store=True)
    ui_company = fields.Float(string='UI (Company)', compute='_compute_insurances', store=True)
    total_insurance_employee = fields.Float(string='Total Insurance (Employee)', 
                                          compute='_compute_insurances', store=True)
    total_insurance_company = fields.Float(string='Total Insurance (Company)', 
                                         compute='_compute_insurances', store=True)
    
    # Tax fields
    skip_pit = fields.Boolean(string='Skip PIT', default=False, help='Skip Personal Income Tax calculation')
    taxable_income = fields.Float(string='Taxable Income', compute='_compute_pit', store=True)
    pit = fields.Float(string='PIT', compute='_compute_pit', store=True)
    
    # Net income
    net_income = fields.Float(string='Net Income', compute='_compute_net_income', store=True)
    
    # Other fields
    note = fields.Text(string='Note')
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                               default=lambda self: self.env.company)
    
    # Payslip lines
    line_ids = fields.One2many('vn.payslip.line', 'payslip_id', string='Payslip Lines')

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_time_off_data(self):
        """Calculate working days and time off data"""
        for payslip in self:
            if not payslip.date_from or not payslip.date_to:
                payslip.total_working_days = 0
                payslip.pto_days = 0
                payslip.unpaid_leave_days = 0
                payslip.actual_working_days = 0
                payslip.paid_working_days = 0
                continue

            # Calculate total working days (Mon-Fri only)
            total_days = 0
            current_date = payslip.date_from
            while current_date <= payslip.date_to:
                if current_date.weekday() < 5:  # Monday to Friday
                    total_days += 1
                current_date += timedelta(days=1)

            payslip.total_working_days = total_days

            # Calculate Time Off data (PTO and Unpaid Leave)
            pto_days = 0
            unpaid_days = 0

            # Check if hr.leave model exists (hr_holidays module installed)
            if payslip.employee_id and 'hr.leave' in self.env:
                # Query time off records for this employee in payslip period
                time_off_records = self.env['hr.leave'].search([
                    ('employee_id', '=', payslip.employee_id.id),
                    ('state', '=', 'validate'),  # Only approved leaves
                    ('date_from', '>=', payslip.date_from),
                    ('date_to', '<=', payslip.date_to),
                ])

                for leave in time_off_records:
                    # Check if this is paid or unpaid leave
                    if leave.holiday_status_id:
                        # Check time off type name or unpaid_leave field
                        if hasattr(leave.holiday_status_id, 'unpaid') and leave.holiday_status_id.unpaid:
                            unpaid_days += leave.number_of_days
                        elif 'unpaid' in leave.holiday_status_id.name.lower() or 'không lương' in leave.holiday_status_id.name.lower():
                            unpaid_days += leave.number_of_days
                        else:
                            # Default to PTO if not explicitly unpaid
                            pto_days += leave.number_of_days

            payslip.pto_days = pto_days
            payslip.unpaid_leave_days = unpaid_days
            payslip.actual_working_days = total_days - pto_days - unpaid_days
            payslip.paid_working_days = payslip.actual_working_days + pto_days

    def _calculate_gross_wage(self):
        """Calculate and update gross wage (not a computed field anymore)"""
        for payslip in self:
            payslip.gross_wage = payslip.basic_wage + payslip.allowances
    
    @api.depends('contract_id', 'gross_wage')
    def _compute_insurances(self):
        for payslip in self:
            if not payslip.contract_id:
                payslip.si_employee = 0.0
                payslip.hi_employee = 0.0
                payslip.ui_employee = 0.0
                payslip.si_company = 0.0
                payslip.hi_company = 0.0
                payslip.ui_company = 0.0
                payslip.total_insurance_employee = 0.0
                payslip.total_insurance_company = 0.0
                continue
                
            # Skip insurance calculation for freelancers and second job
            is_second_job = False
            if payslip.contract_id.structure_type_id:
                is_second_job = payslip.contract_id.vn_structure_type_id.name == 'Second Job'
                
            if payslip.is_freelancer or is_second_job:
                payslip.si_employee = 0.0
                payslip.hi_employee = 0.0
                payslip.ui_employee = 0.0
                payslip.si_company = 0.0
                payslip.hi_company = 0.0
                payslip.ui_company = 0.0
                payslip.total_insurance_employee = 0.0
                payslip.total_insurance_company = 0.0
                continue
                
            # Get insurance rates from config
            config = self.env['vn.payroll.config'].get_config()
            
            # Get insurance wage from contract
            insurance_wage = payslip.contract_id.vn_insurance_wage or payslip.gross_wage
            
            # Calculate SI (Social Insurance)
            si_wage = min(insurance_wage, config.vn_si_salary_cap)
            payslip.si_employee = si_wage * config.vn_si_rate_employee / 100
            payslip.si_company = si_wage * config.vn_si_rate_company / 100
            
            # Calculate HI (Health Insurance)
            hi_wage = min(insurance_wage, config.vn_hi_salary_cap)
            payslip.hi_employee = hi_wage * config.vn_hi_rate_employee / 100
            payslip.hi_company = hi_wage * config.vn_hi_rate_company / 100
            
            # Calculate UI (Unemployment Insurance)
            ui_wage = min(insurance_wage, config.vn_ui_salary_cap)
            payslip.ui_employee = ui_wage * config.vn_ui_rate_employee / 100
            payslip.ui_company = ui_wage * config.vn_ui_rate_company / 100
            
            # Calculate totals
            payslip.total_insurance_employee = payslip.si_employee + payslip.hi_employee + payslip.ui_employee
            payslip.total_insurance_company = payslip.si_company + payslip.hi_company + payslip.ui_company
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New Payslip')) == _('New Payslip'):
                # Generate name based on employee and date
                if vals.get('employee_id') and vals.get('date_to'):
                    employee = self.env['hr.employee'].browse(vals['employee_id'])
                    date_to = fields.Date.to_date(vals['date_to'])
                    month_year = date_to.strftime('%m - %Y')
                    vals['name'] = f"{employee.name} Tháng {month_year}"
                else:
                    # Fallback to sequence for payslip number
                    vals['name'] = self.env['ir.sequence'].next_by_code('vn.payslip') or _('New Payslip')
        return super(VnPayslip, self).create(vals_list)

    @api.depends('gross_wage', 'total_insurance_employee', 'contract_id', 'skip_pit')
    def _compute_pit(self):
        for payslip in self:
            # Check if PIT is skipped
            if payslip.skip_pit:
                payslip.taxable_income = 0.0
                payslip.pit = 0.0
                continue

            if not payslip.contract_id:
                payslip.taxable_income = 0.0
                payslip.pit = 0.0
                continue
                
            # Check if freelancer - apply tax based on freelancer tax table
            if payslip.is_freelancer:
                payslip.taxable_income = payslip.gross_wage
                # Find applicable tax rate from freelancer tax table
                tax_table = self.env['vn.freelancer.tax.table'].search([
                    ('income_from', '<=', payslip.gross_wage),
                    ('income_to', '>', payslip.gross_wage),
                    ('company_id', 'in', [payslip.company_id.id, False])
                ], limit=1)
                
                if tax_table:
                    # Calculate PIT using tax rate and fixed deduction
                    payslip.pit = (payslip.gross_wage * tax_table.tax_rate / 100) - tax_table.fixed_deduction
                else:
                    # Fallback to default 10% if no tax table found
                    payslip.pit = payslip.gross_wage * 0.10
                continue
                
            # For regular employees - calculate using progressive tax
            # Calculate taxable income
            taxable_income = payslip.gross_wage - payslip.total_insurance_employee
            
            # Subtract personal deduction
            personal_deduction = payslip.contract_id.vn_personal_deduction
            taxable_income -= personal_deduction
            
            # Subtract dependant deduction
            dependant_deduction = payslip.contract_id.vn_dependant_deduction * payslip.contract_id.vn_number_of_dependants
            taxable_income -= dependant_deduction
            
            # Ensure taxable income is not negative
            taxable_income = max(0, taxable_income)
            payslip.taxable_income = taxable_income
            
            # Calculate PIT using tax table
            payslip.pit = self.env['vn.pit.tax.table'].calculate_tax(taxable_income)
    
    @api.model
    def compute_pit(self, taxable_income, config):
        """Compute PIT based on taxable income and tax brackets"""
        # Find the applicable tax bracket
        tax_table = self.env['vn.pit.tax.table'].search([], order='income_from')
        
        # Iterate through tax brackets to find the applicable one
        for bracket in tax_table:
            if taxable_income >= bracket.income_from and taxable_income <= bracket.income_to:
                # Calculate PIT
                pit = (taxable_income - bracket.income_from) * bracket.tax_rate / 100
                return pit
        
        # If no applicable tax bracket is found, return 0
        return 0.0
    
    @api.depends('gross_wage', 'total_insurance_employee', 'pit', 'contract_id')
    def _compute_net_income(self):
        for payslip in self:
            if not payslip.contract_id:
                payslip.net_income = 0.0
                continue
                
            # Calculate net income
            net_income = payslip.gross_wage - payslip.total_insurance_employee - payslip.pit
            
            # Subtract union fee if any
            if payslip.contract_id.vn_union_fee:
                net_income -= payslip.contract_id.vn_union_fee
                
            payslip.net_income = net_income
    
    def _generate_payslip_name(self):
        """Generate payslip name based on employee and period"""
        if self.employee_id and self.date_to:
            # Format: "Nguyen Van A Tháng 10 - 2025"
            month_year = self.date_to.strftime('%m - %Y')
            return f"{self.employee_id.name} Tháng {month_year}"
        return _('New Payslip')

    @api.onchange('employee_id', 'date_to')
    def _onchange_employee_or_date(self):
        """Update payslip name when employee or date changes"""
        if self.employee_id and self.date_to:
            self.name = self._generate_payslip_name()

        # Keep existing employee logic
        if self.employee_id and not self.contract_id:
            # Find valid contract for this employee
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'open')
            ], limit=1)

            if contract:
                self.contract_id = contract.id
                self.basic_wage = contract.vn_basic_wage or contract.wage

    @api.onchange('contract_id')
    def _onchange_contract(self):
        if self.contract_id:
            self.basic_wage = self.contract_id.vn_basic_wage or self.contract_id.wage
    
    def action_payslip_draft(self):
        return self.write({'state': 'draft'})
    
    def action_payslip_verify(self):
        return self.write({'state': 'verify'})
    
    def action_payslip_done(self):
        if not self.line_ids:
            self._generate_payslip_lines()
        return self.write({'state': 'done'})
    
    def action_payslip_cancel(self):
        return self.write({'state': 'cancel'})
    
    def unlink(self):
        for payslip in self:
            if payslip.state not in ('draft', 'cancel'):
                raise ValidationError(_("You cannot delete a payslip which is not in draft or cancelled state"))
        return super(VnPayslip, self).unlink()
    
    def force_unlink(self):
        """Force delete payslip regardless of state - only for admin users"""
        self.ensure_one()
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_("Only administrators can force delete payslips"))
        
        # If payslip is in draft or cancel state, show notification that normal delete can be used
        if self.state in ('draft', 'cancel'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Information'),
                    'message': _('This payslip can be deleted normally using the Delete option.'),
                    'sticky': False,
                    'type': 'info',
                }
            }
            
        # Check if confirmation is needed
        if not self.env.context.get('force_delete_confirm'):
            return {
                'type': 'ir.actions.act_window',
                'name': _('Confirm Force Delete'),
                'res_model': 'vn.payslip.force.delete.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_payslip_id': self.id, 'default_payslip_ids': False}
            }
        
        return self.force_unlink_confirmed()
    
    def force_unlink_confirmed(self):
        """Actually perform the force delete after confirmation"""
        self.ensure_one()
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_("Only administrators can force delete payslips"))
            
        # Actual deletion
        if self.line_ids:
            self.line_ids.unlink()
        self.env.cr.execute("DELETE FROM vn_payslip WHERE id=%s", (self.id,))
        return {'type': 'ir.actions.client', 'tag': 'reload'}
        
    def force_unlink_multi(self):
        """Force delete multiple payslips regardless of state - only for admin users"""
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_("Only administrators can force delete payslips"))
            
        # Filter payslips that need force delete (not in draft or cancel state)
        to_force_delete = self.filtered(lambda r: r.state not in ('draft', 'cancel'))
        
        # If no payslips need force delete, show notification
        if not to_force_delete:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Information'),
                    'message': _('Selected payslips can be deleted normally using the Delete option.'),
                    'sticky': False,
                    'type': 'info',
                }
            }
        
        # Check if confirmation is needed
        if not self.env.context.get('force_delete_confirm'):
            return {
                'type': 'ir.actions.act_window',
                'name': _('Confirm Force Delete'),
                'res_model': 'vn.payslip.force.delete.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_payslip_id': False, 'default_payslip_ids': to_force_delete.ids}
            }
        
        return self.force_unlink_multi_confirmed()
    
    def force_unlink_multi_confirmed(self):
        """Actually perform the force delete after confirmation for multiple records"""
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_("Only administrators can force delete payslips"))
            
        # If we have active_ids in context, use those instead
        if self.env.context.get('active_ids'):
            self = self.browse(self.env.context.get('active_ids'))
        
        # Store IDs before deletion for notification
        payslip_count = len(self)
        
        # Delete related records first
        for payslip in self:
            if payslip.line_ids:
                payslip.line_ids.unlink()
        
        # Use SQL to bypass ORM restrictions
        if self.ids:
            self.env.cr.execute("DELETE FROM vn_payslip WHERE id IN %s", (tuple(self.ids),))
        
        # Return notification and reload view
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(f'{payslip_count} payslips have been permanently deleted.'),
                'sticky': False,
                'type': 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }
    
    def _generate_payslip_lines(self):
        """Generate payslip lines based on calculations"""
        for payslip in self:
            # Delete existing lines
            payslip.line_ids.unlink()
            
            lines_vals = []
            
            # Basic wage
            lines_vals.append({
                'payslip_id': payslip.id,
                'name': _('Basic Wage'),
                'code': 'BASIC',
                'amount': payslip.basic_wage,
                'sequence': 1,
            })
            
            # Allowances
            if payslip.allowances:
                lines_vals.append({
                    'payslip_id': payslip.id,
                    'name': _('Allowances'),
                    'code': 'ALW',
                    'amount': payslip.allowances,
                    'sequence': 2,
                })
            
            # Gross wage
            lines_vals.append({
                'payslip_id': payslip.id,
                'name': _('Gross Wage'),
                'code': 'GROSS',
                'amount': payslip.gross_wage,
                'sequence': 5,
            })
            
            # Social Insurance (Employee)
            lines_vals.append({
                'payslip_id': payslip.id,
                'name': _('Social Insurance (Employee)'),
                'code': 'SI_EE',
                'amount': -payslip.si_employee,
                'sequence': 10,
            })
            
            # Health Insurance (Employee)
            lines_vals.append({
                'payslip_id': payslip.id,
                'name': _('Health Insurance (Employee)'),
                'code': 'HI_EE',
                'amount': -payslip.hi_employee,
                'sequence': 11,
            })
            
            # Unemployment Insurance (Employee)
            lines_vals.append({
                'payslip_id': payslip.id,
                'name': _('Unemployment Insurance (Employee)'),
                'code': 'UI_EE',
                'amount': -payslip.ui_employee,
                'sequence': 12,
            })
            
            # Union fee if any
            if payslip.contract_id.vn_union_fee:
                lines_vals.append({
                    'payslip_id': payslip.id,
                    'name': _('Union Fee'),
                    'code': 'UNION',
                    'amount': -payslip.contract_id.vn_union_fee,
                    'sequence': 15,
                })
            
            # Personal Income Tax
            lines_vals.append({
                'payslip_id': payslip.id,
                'name': _('Personal Income Tax'),
                'code': 'PIT',
                'amount': -payslip.pit,
                'sequence': 20,
            })
            
            # Net Income
            lines_vals.append({
                'payslip_id': payslip.id,
                'name': _('Net Income'),
                'code': 'NET',
                'amount': payslip.net_income,
                'sequence': 100,
            })
            
            # Create lines
            self.env['vn.payslip.line'].create(lines_vals)
    
    def get_worked_hours_from_timesheet(self):
        """Get worked hours from timesheet for freelancers"""
        self.ensure_one()
        if not self.is_freelancer or not self.employee_id or not self.date_from or not self.date_to:
            return False
            
        # Check if hr_timesheet module is installed
        if not self.env['ir.module.module'].sudo().search([('name', '=', 'hr_timesheet'), ('state', '=', 'installed')]):
            raise UserError(_('Timesheet module is not installed. Cannot fetch timesheet hours.'))
            
        # Get timesheet entries for this employee within the payslip period
        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        
        # Use timesheet.line model if it exists
        if self.env['ir.model'].sudo().search([('model', '=', 'account.analytic.line')]):
            timesheet_lines = self.env['account.analytic.line'].search(domain)

            # Lấy danh sách ngày nghỉ có lương (leave) để loại trừ
            leave_dates = set()
            if self.employee_id and 'hr.leave' in self.env:
                leave_records = self.env['hr.leave'].search([
                    ('employee_id', '=', self.employee_id.id),
                    ('state', '=', 'validate'),
                    ('date_from', '>=', self.date_from),
                    ('date_to', '<=', self.date_to),
                ])
                for leave in leave_records:
                    # Collect tất cả ngày trong khoảng leave
                    leave_date = leave.date_from.date() if hasattr(leave.date_from, 'date') else leave.date_from
                    leave_date_to = leave.date_to.date() if hasattr(leave.date_to, 'date') else leave.date_to
                    current = leave_date
                    while current <= leave_date_to:
                        leave_dates.add(current)
                        current += timedelta(days=1)

            # Chỉ tính giờ những ngày không phải ngày nghỉ
            total_hours = sum(
                line.unit_amount for line in timesheet_lines
                if (line.date.date() if hasattr(line.date, 'date') else line.date) not in leave_dates
            )

            _logger.info(f'total_hours (excluding leave days): {total_hours}, leave_dates: {leave_dates}')
            wage_type = self.contract_id.wage_type if hasattr(self.contract_id, 'wage_type') else 'monthly'
            if wage_type == 'hourly':
                self.worked_hours = total_hours
            else:
                self.worked_hours = 0
            return True
        else:
            raise UserError(_('Timesheet model not found. Cannot fetch timesheet hours.'))

    def compute_sheet(self):
        """Compute all values of the payslip"""
        for payslip in self:
            # For freelancers, automatically get worked hours from timesheet
            if payslip.is_freelancer and payslip.worked_hours <= 0:
                payslip.get_worked_hours_from_timesheet()

            # Invalidate cache for computed fields to force recalculation
            payslip.invalidate_recordset([
                'total_working_days', 'pto_days', 'unpaid_leave_days',
                'actual_working_days', 'paid_working_days',
                'si_employee', 'hi_employee', 'ui_employee',
                'si_company', 'hi_company', 'ui_company',
                'total_insurance_employee', 'total_insurance_company',
                'taxable_income', 'pit', 'net_income'
            ])
            # Note: gross_wage is now a regular field, not computed

            # Compute time off data first (for monthly wage calculation)
            payslip._compute_time_off_data()

            # Recalculate basic_wage and gross_wage based on wage type
            if payslip.contract_id:
                wage_type = payslip.contract_id.wage_type if hasattr(payslip.contract_id, 'wage_type') else 'monthly'

                if wage_type == 'monthly' and payslip.total_working_days > 0:
                    # Monthly wage: calculate based on paid working days
                    wage_amount = payslip.contract_id.wage or 0
                    daily_rate = wage_amount / payslip.total_working_days
                    new_basic_wage = daily_rate * payslip.paid_working_days
                    new_gross_wage = new_basic_wage + payslip.allowances

                    # Write to database
                    payslip.write({
                        'basic_wage': new_basic_wage,
                        'gross_wage': new_gross_wage
                    })

                elif wage_type == 'hourly':
                    # Hourly wage: calculate based on worked hours
                    hourly_rate = payslip.contract_id.wage or 0
                    new_basic_wage = hourly_rate * payslip.worked_hours
                    new_gross_wage = new_basic_wage + payslip.allowances

                    # Write to database
                    payslip.write({
                        'basic_wage': new_basic_wage,
                        'gross_wage': new_gross_wage
                    })
            else:
                # No contract, just calculate gross_wage from existing basic_wage
                payslip._calculate_gross_wage()

            # Compute insurances based on updated gross_wage
            payslip._compute_insurances()
            payslip._compute_pit()
            payslip._compute_net_income()
            payslip._generate_payslip_lines()
        return True
        
    def action_payslip_preview_payslip(self):
        """Open the payslip preview in a new tab"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/html/vn_hr_payroll.report_vn_payslip/%s' % self.id,
            'target': 'new',
        }
        
    def action_payslip_send_email(self):
        """Send payslip by email to employee"""
        self.ensure_one()
        if not self.employee_id.work_email:
            raise UserError(_('The employee does not have an email address.'))
            
        # Generate PDF report using direct method
        report_name = 'vn_hr_payroll.report_vn_payslip'
        pdf_content, content_type = self.env['ir.actions.report'].with_context(lang=self.env.user.lang)._render_qweb_pdf(
            report_name, [self.id], data={'model': 'vn.payslip'}
        )

        # Generate random password (8 characters: letters + digits)
        pdf_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        # Encrypt PDF with password
        if PdfReader and PdfWriter:
            try:
                # Read the generated PDF
                pdf_reader = PdfReader(io.BytesIO(pdf_content))
                pdf_writer = PdfWriter()

                # Copy all pages
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)

                # Encrypt with password
                pdf_writer.encrypt(user_password=pdf_password, owner_password=None, algorithm="AES-256")

                # Write encrypted PDF to bytes
                encrypted_pdf_buffer = io.BytesIO()
                pdf_writer.write(encrypted_pdf_buffer)
                pdf_content = encrypted_pdf_buffer.getvalue()

                _logger.info(f'Payslip PDF encrypted successfully for {self.name}')
            except Exception as e:
                _logger.warning(f'Failed to encrypt PDF: {str(e)}. Using unencrypted PDF.')
                pdf_password = None  # Reset password if encryption fails
        else:
            _logger.warning('pypdf not available. PDF will not be encrypted.')
            pdf_password = None

        # Prepare attachment with access token for public download
        attachment_name = f"Payslip - {self.name}.pdf"
        attachment = self.env['ir.attachment'].create({
            'name': attachment_name,
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
            'pdf_password': pdf_password,  # Save password
        })

        # Generate access token for public download (no login required)
        attachment.generate_access_token()

        # Get base URL for preview links
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        # Public download link (no login required)
        public_download_url = f"{base_url}/payslip/download/{attachment.id}/{attachment.access_token}"

        # Private download link (login required)
        preview_url = f"{base_url}/web/content/{attachment.id}?download=true"

        # Get payroll configuration
        payroll_config = self.env['vn.payroll.config'].get_config()
        cc_email = payroll_config.payroll_cc_email if payroll_config else None
        from_email = payroll_config.payroll_from_email if payroll_config and payroll_config.payroll_from_email else None

        # Render custom email template (MailChimp style)
        if payroll_config and (payroll_config.email_header_template or
                               payroll_config.email_content_template or
                               payroll_config.email_footer_template):
            # Use custom template
            email_body, template_vars = payroll_config.render_email_template(self)
            # Update preview URL and attachment info in template
            template_vars['preview_url'] = preview_url  # Login required
            template_vars['public_download_url'] = public_download_url  # No login required
            template_vars['download_url'] = public_download_url  # Alias for public URL
            template_vars['attachment_id'] = str(attachment.id)
            template_vars['access_token'] = attachment.access_token
            template_vars['base_url'] = base_url
            template_vars['pdf_password'] = pdf_password or 'N/A'  # Password to open PDF
            template_vars['password_file'] = pdf_password or 'N/A'  # Alias
            email_body = payroll_config._replace_template_vars(email_body, template_vars)
        else:
            # Fallback to default template
            password_info = f'<p><strong>PDF Password:</strong> {pdf_password}</p>' if pdf_password else ''
            email_body = f'''
                <div style="margin: 0px; padding: 0px;">
                    <p>Dear {self.employee_id.name},</p>
                    <p>Please find attached your payslip for the period {self.date_from} to {self.date_to}.</p>
                    {password_info}
                    <p>You can also download your payslip: <a href="{public_download_url}">Download Payslip</a></p>
                    <p>Best regards,<br/>{self.env.user.name}</p>
                </div>
            '''

        # Render custom subject
        if payroll_config and payroll_config.email_subject_template:
            email_subject = payroll_config.render_email_subject(self)
        else:
            email_subject = f'Payslip - {self.name}'

        # Create mail values
        # Use custom from_email if configured, otherwise use current user's email
        if from_email:
            email_from = f'"{self.env.user.company_id.name}" <{from_email}>'
        else:
            email_from = f'"{self.env.user.company_id.name}" <{self.env.user.email}>'

        mail_values = {
            'subject': email_subject,
            'body_html': email_body,
            'email_from': email_from,
            'email_to': self.employee_id.work_email,
            'attachment_ids': [(4, attachment.id)],
            'model': self._name,
            'res_id': self.id,
            'author_id': self.env.user.partner_id.id,
        }

        # Add CC email if configured
        if cc_email:
            mail_values['email_cc'] = cc_email
        
        # Create and send mail directly
        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send()
        
        # Show success message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Payslip email sent successfully!'),
                'sticky': False,
                'type': 'success',
            }
        }

class VnPayslipLine(models.Model):
    _name = 'vn.payslip.line'
    _description = 'Vietnam Payslip Line'
    _order = 'sequence, id'
    
    payslip_id = fields.Many2one('vn.payslip', string='Payslip', required=True, ondelete='cascade')
    name = fields.Char(string='Description', required=True)
    code = fields.Char(string='Code', required=True)
    amount = fields.Float(string='Amount')
    sequence = fields.Integer(string='Sequence', default=10)
    
    @api.constrains('amount')
    def _check_amount(self):
        for line in self:
            if line.code == 'NET' and line.amount < 0:
                raise ValidationError(_("Net income cannot be negative"))
