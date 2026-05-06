# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.http import request
from datetime import timedelta
import uuid

class VnPayrollConfig(models.Model):
    _name = 'vn.payroll.config'
    _description = 'Vietnam Payroll Configuration'
    
    name = fields.Char(string='Name', default='Vietnam Payroll Configuration')
    active = fields.Boolean(string='Active', default=True)
    
    # Insurance rates for employee
    vn_si_rate_employee = fields.Float(string='SI Rate (Employee)', default=8.0,
                                     help='Social Insurance rate for employee (%)')
    vn_hi_rate_employee = fields.Float(string='HI Rate (Employee)', default=1.5,
                                     help='Health Insurance rate for employee (%)')
    vn_ui_rate_employee = fields.Float(string='UI Rate (Employee)', default=1.0,
                                     help='Unemployment Insurance rate for employee (%)')
    
    # Insurance rates for company
    vn_si_rate_company = fields.Float(string='SI Rate (Company)', default=17.5,
                                    help='Social Insurance rate for company (%)')
    vn_hi_rate_company = fields.Float(string='HI Rate (Company)', default=3.0,
                                    help='Health Insurance rate for company (%)')
    vn_ui_rate_company = fields.Float(string='UI Rate (Company)', default=1.0,
                                    help='Unemployment Insurance rate for company (%)')
    
    # Insurance salary caps
    vn_si_salary_cap = fields.Float(string='SI Salary Cap', default=36000000,
                                  help='Maximum salary for Social Insurance contribution')
    vn_hi_salary_cap = fields.Float(string='HI Salary Cap', default=36000000,
                                  help='Maximum salary for Health Insurance contribution')
    vn_ui_salary_cap = fields.Float(string='UI Salary Cap', default=36000000,
                                  help='Maximum salary for Unemployment Insurance contribution')
    
    # Standard deductions
    vn_personal_deduction = fields.Float(string='Personal Deduction', default=11000000,
                                       help='Standard personal deduction amount')
    vn_dependant_deduction = fields.Float(string='Dependant Deduction', default=4400000,
                                        help='Standard deduction amount per dependant')

    # Email Configuration
    payroll_from_email = fields.Char(string='From Email for Payroll',
                                     help='Email address to use as sender when sending payroll emails. If empty, system default email will be used.')
    payroll_cc_email = fields.Char(string='CC Email for Payroll',
                                   help='Email address to CC when sending payroll emails to employees')

    email_subject_template = fields.Char(string='Email Subject Template',
                                         default='Payslip - {{payslip_reference}} ({{payslip_period}})',
                                         help='Email subject template. Use {{variable}} for dynamic data.')

    # Email Template Configuration (like MailChimp)
    email_header_template = fields.Html(string='Email Header Template',
                                        default='''
<div style="background-color: #f8f9fa; padding: 20px; text-align: center; border-bottom: 2px solid #007bff;">
    <img src="{{company_logo}}" alt="{{company_name}}" style="max-height: 60px; margin-bottom: 10px;"/>
    <h2 style="color: #007bff; margin: 0;">{{company_name}}</h2>
    <p style="margin: 5px 0 0 0; color: #6c757d;">Payroll Department</p>
</div>
                                        ''',
                                        help='HTML template for email header. Use {{variable}} for dynamic data.')

    email_content_template = fields.Html(string='Email Content Template',
                                         default='''
<div style="padding: 30px 20px; background-color: #ffffff;">
    <h3 style="color: #333; margin-bottom: 20px;">Dear {{employee_name}},</h3>

    <p style="line-height: 1.6; color: #555;">
        We hope this email finds you well. Please find attached your payslip for the period
        <strong>{{date_from}} to {{date_to}}</strong>.
    </p>

    <div style="background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0;">
        <p style="margin: 0; color: #1976d2;">
            <strong>Payslip Details:</strong><br/>
            Reference: {{payslip_reference}}<br/>
            Period: {{payslip_period}}<br/>
            Net Pay: {{net_pay}}
        </p>
    </div>

    <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
        <p style="margin: 0; color: #856404;">
            <strong>🔐 PDF Password:</strong><br/>
            <span style="font-size: 18px; font-weight: bold; letter-spacing: 2px;">{{pdf_password}}</span>
        </p>
        <p style="margin: 10px 0 0 0; font-size: 12px; color: #856404;">
            Use this password to open your payslip PDF file.
        </p>
    </div>

    <p style="line-height: 1.6; color: #555; text-align: center;">
        <a href="{{download_url}}" style="display: inline-block; padding: 12px 30px; background-color: #007bff; color: #ffffff; text-decoration: none; border-radius: 5px; font-weight: bold;">
            Download Payslip PDF
        </a>
    </p>

    <p style="line-height: 1.6; color: #999; font-size: 12px; text-align: center;">
        No login required. Link expires when payslip is deleted.
    </p>

    <p style="line-height: 1.6; color: #555;">
        If you have any questions regarding your payslip, please don't hesitate to contact our HR department.
    </p>
</div>
                                         ''',
                                         help='HTML template for email content. Use {{variable}} for dynamic data.')

    email_footer_template = fields.Html(string='Email Footer Template',
                                        default='''
<div style="background-color: #343a40; color: #ffffff; padding: 20px; text-align: center;">
    <p style="margin: 0 0 10px 0; font-size: 14px;">
        <strong>{{company_name}}</strong><br/>
        {{company_address}}<br/>
        Phone: {{company_phone}} | Email: {{company_email}}
    </p>

    <div style="border-top: 1px solid #6c757d; padding-top: 15px; margin-top: 15px;">
        <p style="margin: 0; font-size: 12px; color: #adb5bd;">
            This is an automated message. Please do not reply to this email.<br/>
            © {{current_year}} {{company_name}}. All rights reserved.
        </p>
    </div>
</div>
                                        ''',
                                        help='HTML template for email footer. Use {{variable}} for dynamic data.')

    # Template help text
    email_template_help = fields.Text(string='Available Template Variables',
                                      default='''
Available template variables (use with double curly braces {{variable}}):

EMPLOYEE DATA:
{{employee_name}} - Employee full name
{{employee_email}} - Employee email address
{{employee_id}} - Employee ID/code
{{staff_id}} - Staff ID with ISD prefix (e.g. ISD-003, ISD-010)
{{job_title}} - Employee job title/position
{{bank_account}} - Employee bank account number
{{bank_name}} - Employee bank name
{{salary}} - Contract salary with period (e.g. 1,990,000 (theo Tháng) or 200,000 (theo Giờ))

PAYSLIP DATA:
{{payslip_reference}} - Payslip reference number
{{payslip_period}} - Full period text (e.g. 2025-09-01 to 2025-09-30)
{{payslip_period_mmyyyy}} - Month-Year format (e.g. 09-2025)
{{payslip_period_ddmmyyyy}} - Day/Month/Year format (e.g. 01/09/2025 - 30/09/2025)
{{payslip_period_vi}} - Vietnamese month format (e.g. tháng 09/2025)
{{date_from}} - Period start date
{{date_to}} - Period end date
{{net_pay}} - Net pay amount (formatted)
{{gross_pay}} - Gross pay amount (formatted)
{{time_efforts}} - Worked hours (if > 0) or working days excluding weekends
{{total_working_days}} - Total working days in period (Mon-Fri only)
{{pto_days}} - Paid Time Off days (Ngày nghỉ có lương)
{{unpaid_leave_days}} - Unpaid leave days (Nghỉ không lương)
{{actual_working_days}} - Actual days worked (total - PTO - unpaid)
{{paid_working_days}} - Days used for salary calculation (actual + PTO)
{{actual_working_wage}} - Salary for actual working days only (salary / total_working_days × actual_working_days)
{{pto_wage}} - Salary for PTO days (salary / total_working_days × pto_days)
{{unpaid_wage}} - Salary deduction for unpaid leave days (salary / total_working_days × unpaid_leave_days)

WAGE DETAILS:
{{basic_wage}} - Basic wage/salary amount (formatted)
{{allowances}} - Total allowances amount (formatted)
{{allowances_note}} - Notes/description from payslip Notes tab
{{gross_wage}} - Gross wage (basic + allowances) (formatted)
{{worked_hours}} - Total worked hours

EMPLOYEE INSURANCE:
{{si_employee}} - Social Insurance employee contribution (formatted)
{{hi_employee}} - Health Insurance employee contribution (formatted)
{{ui_employee}} - Unemployment Insurance employee contribution (formatted)
{{total_insurance_employee}} - Total employee insurance contribution (formatted)

COMPANY INSURANCE:
{{si_company}} - Social Insurance company contribution (formatted)
{{hi_company}} - Health Insurance company contribution (formatted)
{{ui_company}} - Unemployment Insurance company contribution (formatted)
{{total_insurance_company}} - Total company insurance contribution (formatted)

TAX DETAILS:
{{taxable_income}} - Taxable income after deductions (formatted)
{{pit}} - Personal Income Tax amount (formatted)
{{dependants}} - Number of dependants for tax deduction
{{dependants_deduction}} - Total tax deduction amount for dependants (formatted)

NET INCOME:
{{net_income}} - Net income (same as net_pay) (formatted)

DOWNLOAD LINKS:
{{download_url}} - Public download link (NO LOGIN REQUIRED) ⭐ RECOMMENDED
{{public_download_url}} - Same as download_url (NO LOGIN REQUIRED)
{{preview_url}} - Private download link (LOGIN REQUIRED)
{{attachment_id}} - Attachment ID only (e.g. 123)
{{access_token}} - Access token for public download
{{base_url}} - Base website URL (e.g. https://example.com)

PDF SECURITY:
{{pdf_password}} - Random password to open encrypted PDF file 🔐
{{password_file}} - Same as pdf_password (alias)

COMPANY DATA:
{{company_name}} - Company name
{{company_logo}} - Company logo URL
{{company_address}} - Company address
{{company_phone}} - Company phone
{{company_email}} - Company email
{{company_website}} - Company website

SYSTEM DATA:
{{current_year}} - Current year
{{current_date}} - Current date
{{sender_name}} - Email sender name

EXAMPLE USAGE:
Dear {{employee_name}}, your payslip for {{payslip_period}} is ready.
Gross Wage: {{gross_wage}}
Tax: {{pit}}
Net Income: {{net_income}}

Public download (NO LOGIN): <a href="{{download_url}}">Download Payslip</a>
PDF Password: {{pdf_password}}

Or build manually: {{base_url}}/payslip/download/{{attachment_id}}/{{access_token}}
Private download (LOGIN REQUIRED): <a href="{{preview_url}}">View Online</a>
                                      ''',
                                      readonly=True)

    # Payslip PDF Template Configuration (like MailChimp for PDF)
    payslip_header_template = fields.Html(string='Payslip Header Template',
                                          default='''
<div style="text-align: center; border-bottom: 2px solid #007bff; padding-bottom: 20px; margin-bottom: 30px;">
    <img src="{{company_logo}}" alt="{{company_name}}" style="max-height: 80px; margin-bottom: 15px;"/>
    <h1 style="color: #007bff; margin: 0; font-size: 28px;">{{company_name}}</h1>
    <p style="margin: 5px 0; color: #6c757d; font-size: 14px;">{{company_address}}</p>
    <p style="margin: 0; color: #6c757d; font-size: 14px;">Phone: {{company_phone}} | Email: {{company_email}}</p>
</div>

<div style="text-align: center; margin-bottom: 30px;">
    <h2 style="color: #333; margin: 0; font-size: 24px;">PAYSLIP</h2>
    <p style="margin: 5px 0; font-size: 16px; color: #666;">{{payslip_period}}</p>
</div>
                                          ''',
                                          help='HTML template for payslip header (PDF). Use {{variable}} for dynamic data.')

    payslip_content_template = fields.Html(string='Payslip Content Template',
                                           default='''
<!-- Employee Information using table layout for PDF compatibility -->
<table style="width: 100%; margin-bottom: 20px; border-collapse: collapse;">
    <tr>
        <td style="width: 50%; vertical-align: top; padding-right: 20px;">
            <h4 style="margin: 0 0 10px 0; color: #007bff;">Employee Information</h4>
            <p style="margin: 5px 0;"><strong>Name:</strong> {{employee_name}}</p>
            <p style="margin: 5px 0;"><strong>ID:</strong> {{employee_id}}</p>
            <p style="margin: 5px 0;"><strong>Email:</strong> {{employee_email}}</p>
        </td>
        <td style="width: 50%; vertical-align: top; padding-left: 20px;">
            <h4 style="margin: 0 0 10px 0; color: #007bff;">Payslip Details</h4>
            <p style="margin: 5px 0;"><strong>Reference:</strong> {{payslip_reference}}</p>
            <p style="margin: 5px 0;"><strong>Period:</strong> {{payslip_period}}</p>
            <p style="margin: 5px 0;"><strong>Generated:</strong> {{current_date}}</p>
        </td>
    </tr>
</table>

<!-- Salary Breakdown -->
<div style="margin-bottom: 30px;">
    <h4 style="color: #007bff; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Salary Breakdown</h4>

    <table style="width: 100%; border-collapse: collapse; margin-top: 15px; border: 1px solid #ddd;">
        <thead>
            <tr style="background-color: #f8f9fa;">
                <th style="border: 1px solid #ddd; padding: 12px; text-align: left; font-weight: bold;">Description</th>
                <th style="border: 1px solid #ddd; padding: 12px; text-align: right; font-weight: bold;">Amount (VND)</th>
            </tr>
        </thead>
        <tbody>
            <!-- Payslip lines will be inserted here by Odoo QWeb -->
            <t t-foreach="o.line_ids" t-as="line">
                <tr>
                    <td style="border: 1px solid #ddd; padding: 12px;">
                        <t t-esc="line.name"/>
                    </td>
                    <td style="border: 1px solid #ddd; padding: 12px; text-align: right;">
                        <t t-esc="'{:,.0f}'.format(line.amount)"/>
                    </td>
                </tr>
            </t>
        </tbody>
    </table>
</div>

<!-- Summary -->
<table style="width: 100%; background-color: #e3f2fd; margin-top: 20px; border-radius: 5px;">
    <tr>
        <td style="padding: 15px; text-align: right;">
            <h4 style="margin: 0 0 10px 0; color: #1976d2;">Summary</h4>
            <p style="margin: 5px 0; font-size: 16px;"><strong>Gross Pay:</strong> {{gross_pay}}</p>
            <p style="margin: 5px 0; font-size: 18px; color: #1976d2;"><strong>Net Pay:</strong> {{net_pay}}</p>
        </td>
    </tr>
</table>
                                           ''',
                                           help='HTML template for payslip content (PDF). Use {{variable}} for dynamic data and QWeb syntax.')

    payslip_footer_template = fields.Html(string='Payslip Footer Template',
                                          default='''
<div style="margin-top: 40px; border-top: 1px solid #ddd; padding-top: 20px; font-size: 12px; color: #666;">
    <table style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="width: 50%; vertical-align: top;">
                <p style="margin: 0;"><strong>Generated by:</strong> {{sender_name}}</p>
                <p style="margin: 5px 0;"><strong>Date:</strong> {{current_date}}</p>
            </td>
            <td style="width: 50%; vertical-align: top; text-align: right;">
                <p style="margin: 0;"><strong>{{company_name}}</strong></p>
                <p style="margin: 5px 0;">This is a computer-generated document.</p>
            </td>
        </tr>
    </table>

    <div style="text-align: center; margin-top: 15px; font-size: 10px; color: #999;">
        © {{current_year}} {{company_name}}. All rights reserved.
    </div>
</div>
                                          ''',
                                          help='HTML template for payslip footer (PDF). Use {{variable}} for dynamic data.')
    
    @api.constrains('vn_si_rate_employee', 'vn_hi_rate_employee', 'vn_ui_rate_employee',
                   'vn_si_rate_company', 'vn_hi_rate_company', 'vn_ui_rate_company')
    def _check_rates(self):
        for config in self:
            if any(rate < 0 or rate > 100 for rate in [
                config.vn_si_rate_employee, config.vn_hi_rate_employee, config.vn_ui_rate_employee,
                config.vn_si_rate_company, config.vn_hi_rate_company, config.vn_ui_rate_company
            ]):
                raise ValidationError(_('Insurance rates must be between 0 and 100.'))
    
    @api.model
    def get_config(self):
        """Get the active configuration or create default if not exists"""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            config = self.create({})
        return config

    def _calculate_working_days(self, date_from, date_to):
        """Calculate working days (excluding weekends) between two dates"""
        if not date_from or not date_to:
            return 0

        working_days = 0
        current_date = date_from

        while current_date <= date_to:
            # 0 = Monday, 6 = Sunday
            if current_date.weekday() < 5:  # Monday to Friday
                working_days += 1
            current_date += timedelta(days=1)

        return working_days

    def render_email_template(self, payslip):
        """Render email template with dynamic data (MailChimp style)"""
        self.ensure_one()

        # Get data from payslip (already computed)
        company = payslip.company_id
        employee = payslip.employee_id

        # Use payslip computed fields instead of recalculating
        basic_wage = payslip.basic_wage
        allowances = payslip.allowances
        gross_pay = payslip.gross_wage
        net_pay = payslip.net_income

        # Insurance (use payslip computed fields)
        si_employee = payslip.si_employee
        hi_employee = payslip.hi_employee
        ui_employee = payslip.ui_employee
        total_insurance_employee = payslip.total_insurance_employee

        si_company = payslip.si_company
        hi_company = payslip.hi_company
        ui_company = payslip.ui_company
        total_insurance_company = payslip.total_insurance_company

        # Tax
        pit = payslip.pit

        # Working days/hours (use payslip computed fields)
        worked_hours = payslip.worked_hours
        total_working_days = payslip.total_working_days
        pto_days = payslip.pto_days
        unpaid_leave_days = payslip.unpaid_leave_days
        actual_working_days = payslip.actual_working_days
        paid_working_days = payslip.paid_working_days

        # Parse bank account info
        bank_account = ''
        bank_name = ''
        if hasattr(employee, 'bank_account_id') and employee.bank_account_id:
            bank_account = employee.bank_account_id.acc_number or ''
            bank_name = employee.bank_account_id.bank_name or (employee.bank_account_id.bank_id.name if employee.bank_account_id.bank_id else '')
        elif hasattr(employee, 'bank_account') and employee.bank_account:
            parts = employee.bank_account.split(' - ')
            bank_account = parts[0].strip() if len(parts) >= 2 else employee.bank_account
            bank_name = parts[1].strip() if len(parts) >= 2 else ''

        # Format salary, time efforts, and wage breakdown based on wage type
        salary = time_efforts = ''
        actual_working_wage = pto_wage = unpaid_wage = 0

        if payslip.contract_id:
            wage_amount = payslip.contract_id.wage or 0
            wage_type = getattr(payslip.contract_id, 'wage_type', 'monthly')
            is_hourly = wage_type == 'hourly'

            # Format salary and time efforts
            salary = f"{wage_amount:,.0f} (theo {'Giờ' if is_hourly else 'Tháng'})"
            time_efforts = f"{worked_hours:.1f} giờ" if is_hourly else f"{actual_working_days} ngày"

            # Calculate wage breakdown
            if is_hourly:
                actual_working_wage = worked_hours * wage_amount
            elif total_working_days > 0:
                daily_rate = wage_amount / total_working_days
                actual_working_wage = daily_rate * actual_working_days
                pto_wage = daily_rate * pto_days
                unpaid_wage = daily_rate * unpaid_leave_days

        # Format period strings
        payslip_period_ddmmyyyy = payslip_period_vi = ''
        if payslip.date_from and payslip.date_to:
            payslip_period_ddmmyyyy = f"{payslip.date_from.strftime('%d/%m/%Y')} - {payslip.date_to.strftime('%d/%m/%Y')}"
            payslip_period_vi = f"tháng {payslip.date_to.strftime('%m/%Y')}"

        # Get dependants
        dependants = getattr(payslip, 'dependants',
                           getattr(payslip.contract_id, 'vn_number_of_dependants', 0) if payslip.contract_id else 0)
        dependants_deduction = dependants * self.vn_dependant_deduction

        template_vars = {
            # Employee data
            'employee_name': employee.name or '',
            'employee_email': employee.work_email or '',
            'employee_id': employee.barcode or employee.pin or str(employee.id),
            'staff_id': f"ISD-{employee.id:03d}",
            'job_title': employee.job_title or (employee.job_id.name if employee.job_id else ''),
            'bank_account': bank_account,
            'bank_name': bank_name,
            'salary': salary,

            # Payslip data
            'payslip_reference': payslip.name or '',
            'payslip_period': f"{payslip.date_from} to {payslip.date_to}",
            'payslip_period_mmyyyy': payslip.date_to.strftime('%m-%Y') if payslip.date_to else '',
            'payslip_period_ddmmyyyy': payslip_period_ddmmyyyy,
            'payslip_period_vi': payslip_period_vi,
            'date_from': str(payslip.date_from),
            'date_to': str(payslip.date_to),
            'net_pay': f"{net_pay:,.0f} VND" if net_pay else "0 VND",
            'gross_pay': f"{gross_pay:,.0f} VND" if gross_pay else "0 VND",
            'time_efforts': time_efforts,  # Worked hours or working days
            'total_working_days': f"{total_working_days:.1f}",
            'pto_days': f"{pto_days:.1f}" if pto_days else "-",
            'unpaid_leave_days': f"{unpaid_leave_days:.1f}" if unpaid_leave_days else "-",
            'actual_working_days': f"{actual_working_days:.1f}" if actual_working_days else "-",
            'paid_working_days': f"{paid_working_days:.1f}",
            'actual_working_wage': f"{actual_working_wage:,.0f} VND" if actual_working_wage else "- VND",
            'pto_wage': f"{pto_wage:,.0f} VND" if pto_wage else "- VND",
            'unpaid_wage': f"{unpaid_wage:,.0f} VND" if unpaid_wage else "- VND",
            'preview_url': '',  # Will be set in sending function

            # Wage details
            'basic_wage': f"{basic_wage:,.0f} VND" if basic_wage else "0 VND",
            'allowances': f"{allowances:,.0f} VND" if allowances else "- VND",
            'allowances_note': payslip.note or '',
            'gross_wage': f"{gross_pay:,.0f} VND" if gross_pay else "0 VND",
            'worked_hours': f"{worked_hours:.2f}",

            # Employee Insurance (use absolute values for display)
            'si_employee': f"{abs(si_employee):,.0f} VND" if si_employee else "0 VND",
            'hi_employee': f"{abs(hi_employee):,.0f} VND" if hi_employee else "0 VND",
            'ui_employee': f"{abs(ui_employee):,.0f} VND" if ui_employee else "0 VND",
            'total_insurance_employee': f"{total_insurance_employee:,.0f} VND" if total_insurance_employee else "- VND",

            # Company Insurance (use absolute values for display)
            'si_company': f"{abs(si_company):,.0f} VND" if si_company else "0 VND",
            'hi_company': f"{abs(hi_company):,.0f} VND" if hi_company else "0 VND",
            'ui_company': f"{abs(ui_company):,.0f} VND" if ui_company else "0 VND",
            'total_insurance_company': f"{total_insurance_company:,.0f} VND",

            # Tax details
            'taxable_income': f"{payslip.taxable_income:,.0f} VND" if hasattr(payslip, 'taxable_income') else "0 VND",
            'pit': f"{abs(pit):,.0f} VND" if pit else "0 VND",
            'dependants': str(dependants),
            'dependants_deduction': f"{dependants_deduction:,.0f} VND" if dependants_deduction else "- VND",

            # Net income
            'net_income': f"{net_pay:,.0f} VND" if net_pay else "0 VND",

            # Company data
            'company_name': company.name or '',
            'company_logo': f"data:image/png;base64,{company.logo.decode('utf-8')}" if company.logo else '',
            'company_address': company.street or '',
            'company_phone': company.phone or '',
            'company_email': company.email or '',
            'company_website': company.website or '',

            # System data
            'current_year': str(fields.Date.today().year),
            'current_date': str(fields.Date.today()),
            'sender_name': self.env.user.name or '',
        }

        # Render templates
        header = self._replace_template_vars(self.email_header_template or '', template_vars)
        content = self._replace_template_vars(self.email_content_template or '', template_vars)
        footer = self._replace_template_vars(self.email_footer_template or '', template_vars)

        # Combine templates
        full_template = f"""
        <div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
            {header}
            {content}
            {footer}
        </div>
        """

        return full_template, template_vars

    def render_email_subject(self, payslip):
        """Render email subject with dynamic data"""
        self.ensure_one()

        if not self.email_subject_template:
            return f'Payslip - {payslip.name}'

        # Use same template variables as email body
        _, template_vars = self.render_email_template(payslip)

        # Render subject
        subject = self._replace_template_vars(self.email_subject_template, template_vars)
        return subject

    def render_payslip_template(self, payslip):
        """Render payslip PDF template with dynamic data (MailChimp style)"""
        self.ensure_one()

        # Use same template variables as email
        _, template_vars = self.render_email_template(payslip)

        # Render PDF templates
        header = self._replace_template_vars(self.payslip_header_template or '', template_vars)
        content = self._replace_template_vars(self.payslip_content_template or '', template_vars)
        footer = self._replace_template_vars(self.payslip_footer_template or '', template_vars)

        # Combine templates for PDF with UTF-8 encoding
        full_template = f"""
        <meta charset="UTF-8"/>
        <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
            {header}
            {content}
            {footer}
        </div>
        """

        return full_template, template_vars

    def _replace_template_vars(self, template, variables):
        """Replace template variables with actual values"""
        if not template:
            return ''

        rendered = template
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            # Ensure proper encoding for Vietnamese text
            str_value = str(value) if value is not None else ''
            rendered = rendered.replace(placeholder, str_value)

        return rendered

    def _get_mock_template_vars(self):
        """Get mock data for template preview"""
        self.ensure_one()

        return {
            # Employee data
            'employee_name': 'Nguyễn Văn A',
            'employee_email': 'nguyenvana@company.com',
            'employee_id': 'EMP001',
            'staff_id': 'ISD-003',
            'job_title': 'Senior Developer',
            'bank_account': '0859914406',
            'bank_name': 'MBBank',
            'salary': '1,990,000 (theo Tháng)',

            # Payslip data
            'payslip_reference': 'PS/2025/0046',
            'payslip_period': '2025-10-01 to 2025-10-31',
            'payslip_period_mmyyyy': '10-2025',
            'payslip_period_ddmmyyyy': '01/10/2025 - 31/10/2025',
            'payslip_period_vi': 'tháng 10/2025',
            'date_from': '2025-10-01',
            'date_to': '2025-10-31',
            'net_pay': '15,000,000 VND',
            'gross_pay': '18,000,000 VND',
            'time_efforts': '23 days',
            'total_working_days': '23',
            'pto_days': '1.5',
            'unpaid_leave_days': '-',
            'actual_working_days': '21.5',
            'paid_working_days': '23.0',
            'actual_working_wage': '1,860,217 VND',
            'pto_wage': '129,783 VND',
            'unpaid_wage': '- VND',

            # Wage details (formatted)
            'basic_wage': '10,000,000 VND',
            'allowances': '8,000,000 VND',
            'allowances_note': 'Phụ cấp ăn trưa: 1,500,000 VND\nPhụ cấp xăng xe: 1,000,000 VND\nPhụ cấp điện thoại: 500,000 VND',
            'gross_wage': '18,000,000 VND',
            'worked_hours': '0.00',

            # Employee Insurance (formatted)
            'si_employee': '1,440,000 VND',
            'hi_employee': '270,000 VND',
            'ui_employee': '180,000 VND',
            'total_insurance_employee': '1,890,000 VND',

            # Company Insurance (formatted)
            'si_company': '3,150,000 VND',
            'hi_company': '540,000 VND',
            'ui_company': '180,000 VND',
            'total_insurance_company': '3,870,000 VND',

            # Tax details (formatted)
            'taxable_income': '16,110,000 VND',
            'pit': '1,111,000 VND',
            'dependants': '2',
            'dependants_deduction': '8,800,000 VND',

            # Net income (formatted)
            'net_income': '15,000,000 VND',

            # Download links
            'download_url': 'https://example.com/payslip/download/123/abc123token',
            'public_download_url': 'https://example.com/payslip/download/123/abc123token',
            'preview_url': 'https://example.com/web/content/123?download=true',
            'attachment_id': '123',
            'access_token': 'abc123token',
            'base_url': 'https://example.com',

            # PDF Security
            'pdf_password': 'aB3xY7zK',
            'password_file': 'aB3xY7zK',

            # Company data
            'company_name': self.env.company.name or 'Công Ty TNHH IntelliSyncData',
            'company_logo': '',
            'company_address': self.env.company.street or '123 Đường ABC, Quận 1, TP.HCM',
            'company_phone': self.env.company.phone or '(028) 1234 5678',
            'company_email': self.env.company.email or 'hr@company.com',
            'company_website': self.env.company.website or 'https://company.com',

            # System data
            'current_year': str(fields.Date.today().year),
            'current_date': str(fields.Date.today()),
            'sender_name': self.env.user.name or 'HR Manager',
        }

    def action_preview_email_header(self):
        """Preview email header template"""
        self.ensure_one()
        template_vars = self._get_mock_template_vars()
        rendered_html = self._replace_template_vars(self.email_header_template or '', template_vars)

        # Store HTML in session with unique ID
        preview_id = str(uuid.uuid4())
        request.session[f'template_preview_{preview_id}'] = rendered_html

        return {
            'type': 'ir.actions.act_url',
            'url': f'/vn_hr_payroll/template_preview?preview_id={preview_id}',
            'target': 'new',
        }

    def action_preview_email_content(self):
        """Preview email content template"""
        self.ensure_one()
        template_vars = self._get_mock_template_vars()
        rendered_html = self._replace_template_vars(self.email_content_template or '', template_vars)

        # Store HTML in session with unique ID
        preview_id = str(uuid.uuid4())
        request.session[f'template_preview_{preview_id}'] = rendered_html

        return {
            'type': 'ir.actions.act_url',
            'url': f'/vn_hr_payroll/template_preview?preview_id={preview_id}',
            'target': 'new',
        }

    def action_preview_email_footer(self):
        """Preview email footer template"""
        self.ensure_one()
        template_vars = self._get_mock_template_vars()
        rendered_html = self._replace_template_vars(self.email_footer_template or '', template_vars)

        # Store HTML in session with unique ID
        preview_id = str(uuid.uuid4())
        request.session[f'template_preview_{preview_id}'] = rendered_html

        return {
            'type': 'ir.actions.act_url',
            'url': f'/vn_hr_payroll/template_preview?preview_id={preview_id}',
            'target': 'new',
        }

    def action_preview_email_full(self):
        """Preview full email (header + content + footer)"""
        self.ensure_one()
        template_vars = self._get_mock_template_vars()

        header = self._replace_template_vars(self.email_header_template or '', template_vars)
        content = self._replace_template_vars(self.email_content_template or '', template_vars)
        footer = self._replace_template_vars(self.email_footer_template or '', template_vars)

        full_html = f"""
        <div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
            {header}
            {content}
            {footer}
        </div>
        """

        # Store HTML in session with unique ID
        preview_id = str(uuid.uuid4())
        request.session[f'template_preview_{preview_id}'] = full_html

        return {
            'type': 'ir.actions.act_url',
            'url': f'/vn_hr_payroll/template_preview?preview_id={preview_id}',
            'target': 'new',
        }

    def action_preview_payslip_header(self):
        """Preview payslip header template"""
        self.ensure_one()
        template_vars = self._get_mock_template_vars()
        rendered_html = self._replace_template_vars(self.payslip_header_template or '', template_vars)

        # Store HTML in session with unique ID
        preview_id = str(uuid.uuid4())
        request.session[f'template_preview_{preview_id}'] = rendered_html

        return {
            'type': 'ir.actions.act_url',
            'url': f'/vn_hr_payroll/template_preview?preview_id={preview_id}',
            'target': 'new',
        }

    def action_preview_payslip_content(self):
        """Preview payslip content template"""
        self.ensure_one()
        template_vars = self._get_mock_template_vars()
        rendered_html = self._replace_template_vars(self.payslip_content_template or '', template_vars)

        # Store HTML in session with unique ID
        preview_id = str(uuid.uuid4())
        request.session[f'template_preview_{preview_id}'] = rendered_html

        return {
            'type': 'ir.actions.act_url',
            'url': f'/vn_hr_payroll/template_preview?preview_id={preview_id}',
            'target': 'new',
        }

    def action_preview_payslip_footer(self):
        """Preview payslip footer template"""
        self.ensure_one()
        template_vars = self._get_mock_template_vars()
        rendered_html = self._replace_template_vars(self.payslip_footer_template or '', template_vars)

        # Store HTML in session with unique ID
        preview_id = str(uuid.uuid4())
        request.session[f'template_preview_{preview_id}'] = rendered_html

        return {
            'type': 'ir.actions.act_url',
            'url': f'/vn_hr_payroll/template_preview?preview_id={preview_id}',
            'target': 'new',
        }

    def action_preview_payslip_full(self):
        """Preview full payslip PDF (header + content + footer)"""
        self.ensure_one()
        template_vars = self._get_mock_template_vars()

        header = self._replace_template_vars(self.payslip_header_template or '', template_vars)
        content = self._replace_template_vars(self.payslip_content_template or '', template_vars)
        footer = self._replace_template_vars(self.payslip_footer_template or '', template_vars)

        full_html = f"""
        <div style="max-width: 800px; margin: 0 auto; font-family: Arial, sans-serif;">
            {header}
            {content}
            {footer}
        </div>
        """

        # Store HTML in session with unique ID
        preview_id = str(uuid.uuid4())
        request.session[f'template_preview_{preview_id}'] = full_html

        return {
            'type': 'ir.actions.act_url',
            'url': f'/vn_hr_payroll/template_preview?preview_id={preview_id}',
            'target': 'new',
        }
