# -*- coding: utf-8 -*-

from odoo import models, fields


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    pdf_password = fields.Char(
        string='PDF Password',
        help='Password to open encrypted PDF file (for payslip)'
    )
