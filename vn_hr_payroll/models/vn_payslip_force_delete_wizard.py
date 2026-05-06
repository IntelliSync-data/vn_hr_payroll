from odoo import models, fields, api, _
from odoo.exceptions import UserError


class VnPayslipForceDeleteWizard(models.TransientModel):
    _name = 'vn.payslip.force.delete.wizard'
    _description = 'Confirm Force Delete Payslips'

    payslip_id = fields.Many2one('vn.payslip', string='Payslip')
    payslip_ids = fields.Many2many('vn.payslip', string='Payslips')
    confirmation_message = fields.Html(string='Confirmation', compute='_compute_confirmation_message')
    
    @api.depends('payslip_id', 'payslip_ids')
    def _compute_confirmation_message(self):
        for wizard in self:
            if wizard.payslip_id:
                wizard.confirmation_message = _('Are you sure you want to force delete this payslip?')
            elif wizard.payslip_ids:
                count = len(wizard.payslip_ids)
                wizard.confirmation_message = _('Are you sure you want to force delete %s payslips?') % count
            else:
                wizard.confirmation_message = _('No payslips selected for force delete.')
    
    def action_confirm(self):
        """Confirm force deletion of payslips"""
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_("Only administrators can force delete payslips"))
            
        if self.payslip_id:
            return self.payslip_id.with_context(force_delete_confirm=True).force_unlink_confirmed()
        elif self.payslip_ids:
            return self.payslip_ids.with_context(force_delete_confirm=True).force_unlink_multi_confirmed()
        
        return {'type': 'ir.actions.act_window_close'}
    
    def action_cancel(self):
        """Cancel the force deletion"""
        return {'type': 'ir.actions.act_window_close'}
