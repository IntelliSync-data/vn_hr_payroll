# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class PayslipSchedule(models.Model):
    _name = 'vn.payslip.schedule'
    _description = 'Payslip Schedule'
    _order = 'name'

    name = fields.Char(string='Schedule Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    day_of_month = fields.Integer(
        string='Day of Month',
        required=True,
        default=1,
        help='Day of the month to generate payslips (1-31). If day exceeds month days, last day will be used.'
    )
    payslip_period_type = fields.Selection([
        ('previous_month', 'Previous Month'),
        ('current_month', 'Current Month'),
    ], string='Payslip Period', required=True, default='previous_month',
       help='Previous Month: Generate payslip for the month before generation date.\n'
            'Current Month: Generate payslip for the same month as generation date.')
    description = fields.Text(string='Description')
    employee_ids = fields.Many2many(
        'hr.employee',
        'payslip_schedule_employee_rel',
        'schedule_id',
        'employee_id',
        string='Employees',
        domain="[('contract_ids', '!=', False)]",
        help='Select employees with active contracts'
    )
    employee_count = fields.Integer(
        string='Employee Count',
        compute='_compute_employee_count',
        store=True
    )
    last_generated_date = fields.Date(string='Last Generated Date', readonly=True)
    next_generation_date = fields.Date(
        string='Next Generation Date',
        compute='_compute_next_generation_date',
        store=True
    )
    payslip_ids = fields.One2many(
        'vn.payslip',
        'schedule_id',
        string='Generated Payslips'
    )
    payslip_count = fields.Integer(
        string='Payslip Count',
        compute='_compute_payslip_count'
    )

    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for schedule in self:
            schedule.employee_count = len(schedule.employee_ids)

    @api.depends('payslip_ids')
    def _compute_payslip_count(self):
        for schedule in self:
            schedule.payslip_count = len(schedule.payslip_ids)

    @api.depends('day_of_month', 'last_generated_date')
    def _compute_next_generation_date(self):
        for schedule in self:
            today = fields.Date.today()

            if schedule.last_generated_date:
                # Next month from last generated date
                base_date = schedule.last_generated_date + relativedelta(months=1)
            else:
                # Not generated yet - calculate based on current date
                base_date = today

            # Set to the configured day of month
            year = base_date.year
            month = base_date.month
            day = schedule.day_of_month

            # Handle case where day exceeds month's max days
            try:
                next_date = fields.Date.from_string(f'{year}-{month:02d}-{day:02d}')
            except ValueError:
                # Use last day of month if day is invalid
                next_date = fields.Date.from_string(f'{year}-{month:02d}-01') + relativedelta(months=1, days=-1)

            # If the calculated date is in the past, move to next month
            if next_date < today:
                next_date = next_date + relativedelta(months=1)
                # Re-validate day for next month
                try:
                    next_date = fields.Date.from_string(f'{next_date.year}-{next_date.month:02d}-{day:02d}')
                except ValueError:
                    next_date = fields.Date.from_string(f'{next_date.year}-{next_date.month:02d}-01') + relativedelta(months=1, days=-1)

            schedule.next_generation_date = next_date

    @api.constrains('day_of_month')
    def _check_day_of_month(self):
        for schedule in self:
            if schedule.day_of_month < 1 or schedule.day_of_month > 31:
                raise ValidationError(_('Day of month must be between 1 and 31.'))

    def action_generate_payslips(self, manual=True):
        """Generate payslips for all employees in this schedule

        Args:
            manual (bool): True if triggered by "Generate Now" button, False if triggered by cron
        """
        self.ensure_one()

        if not self.employee_ids:
            raise UserError(_('Please select at least one employee.'))

        # Calculate payslip period
        today = fields.Date.today()

        if manual:
            # Generate Now: Always generate for current month
            date_from = today.replace(day=1)  # First day of current month
            date_to = (date_from + relativedelta(months=1)) - timedelta(days=1)  # Last day of current month
        else:
            # Cron auto-generation: Use payslip_period_type
            if self.payslip_period_type == 'current_month':
                # Generate for current month
                date_from = today.replace(day=1)  # First day of current month
                date_to = (date_from + relativedelta(months=1)) - timedelta(days=1)  # Last day of current month
            else:
                # Generate for previous month
                date_to = today.replace(day=1) - timedelta(days=1)  # Last day of previous month
                date_from = date_to.replace(day=1)  # First day of previous month

        generated_payslips = self.env['vn.payslip']
        skipped_employees = []

        for employee in self.employee_ids:
            # Get active contract for the employee
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'open'),
                ('date_start', '<=', date_to),
                '|',
                ('date_end', '=', False),
                ('date_end', '>=', date_from)
            ], limit=1)

            if not contract:
                skipped_employees.append(employee.name)
                _logger.warning(f'No active contract found for employee {employee.name}')
                continue

            # Check if payslip already exists for this period
            existing_payslip = self.env['vn.payslip'].search([
                ('employee_id', '=', employee.id),
                ('date_from', '=', date_from),
                ('date_to', '=', date_to),
            ], limit=1)

            if existing_payslip:
                _logger.info(f'Payslip already exists for {employee.name} for period {date_from} to {date_to}')
                skipped_employees.append(f"{employee.name} (already exists)")
                continue

            # Create payslip in draft state
            payslip_vals = {
                'employee_id': employee.id,
                'contract_id': contract.id,
                'date_from': date_from,
                'date_to': date_to,
                'schedule_id': self.id,
                'state': 'draft',  # Create in draft state
            }

            try:
                payslip = self.env['vn.payslip'].create(payslip_vals)
                # Compute payslip lines
                payslip.compute_sheet()
                generated_payslips |= payslip
                _logger.info(f'Generated payslip {payslip.name} for employee {employee.name}')
            except Exception as e:
                skipped_employees.append(f"{employee.name} (error: {str(e)})")
                _logger.error(f'Failed to generate payslip for {employee.name}: {str(e)}')

        # Update last generated date
        self.last_generated_date = fields.Date.today()

        # Prepare notification message
        message = _('Generated %d payslip(s) successfully.') % len(generated_payslips)
        if skipped_employees:
            message += _('\n\nSkipped employees:\n- %s') % '\n- '.join(skipped_employees)

        # Show notification
        if generated_payslips:
            # Return action to show generated payslips
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'vn.payslip',
                'view_mode': 'list,form',
                'domain': [('id', 'in', generated_payslips.ids)],
                'name': _('Generated Payslips'),
                'context': {
                    'default_schedule_id': self.id,
                }
            }
        else:
            # No payslips generated, show warning notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Payslip Generation'),
                    'message': message,
                    'type': 'warning',
                    'sticky': False,
                }
            }

    @api.model
    def cron_generate_payslips(self):
        """Cron job to automatically generate payslips based on schedule"""
        today = fields.Date.today()

        # Find all active schedules that need to generate today
        schedules = self.search([
            ('active', '=', True),
            ('next_generation_date', '<=', today),
        ])

        _logger.info(f'Cron: Found {len(schedules)} schedule(s) to process')

        for schedule in schedules:
            try:
                _logger.info(f'Cron: Generating payslips for schedule {schedule.name}')
                schedule.action_generate_payslips(manual=False)
            except Exception as e:
                _logger.error(f'Cron: Failed to generate payslips for schedule {schedule.name}: {str(e)}')

    def action_view_payslips(self):
        """View all payslips generated by this schedule"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generated Payslips'),
            'res_model': 'vn.payslip',
            'view_mode': 'list,form',
            'domain': [('schedule_id', '=', self.id)],
            'context': {'default_schedule_id': self.id},
        }
