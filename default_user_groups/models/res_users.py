# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to add default groups to new users"""
        users = super(ResUsers, self).create(vals_list)
        
        # Get default groups from system parameters
        default_group_ids = self._get_default_groups()
        
        if default_group_ids:
            for user in users:
                # Skip adding groups to admin and demo users
                if user.login in ('admin', 'demo'):
                    continue
                    
                # Skip if user already has groups assigned (from vals_list)
                current_groups = user.groups_id.ids
                groups_to_add = [gid for gid in default_group_ids if gid not in current_groups]
                
                if groups_to_add:
                    user.write({
                        'groups_id': [(4, group_id) for group_id in groups_to_add]
                    })
                    
                    group_names = self.env['res.groups'].browse(groups_to_add).mapped('name')
                    _logger.info(f"Added default groups {group_names} to user {user.name} ({user.login})")
        
        return users

    def _get_default_groups(self):
        """Get default groups from system parameters"""
        import json
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        
        # Get default group IDs from JSON parameter
        default_groups_json = IrConfigParameter.get_param('default_user_groups.group_ids_json', '[]')
        
        try:
            group_ids = json.loads(default_groups_json)
            if group_ids:
                # Verify groups exist
                existing_groups = self.env['res.groups'].browse(group_ids).exists()
                return existing_groups.ids
        except (json.JSONDecodeError, TypeError) as e:
            _logger.warning(f"Invalid default groups JSON parameter: {default_groups_json}. Error: {e}")
        
        return []

    @api.model
    def signup(self, values, token=None):
        """Override signup to ensure default groups are added during invitation signup"""
        result = super(ResUsers, self).signup(values, token)
        
        # Find the created user and add default groups if needed
        if 'login' in values:
            user = self.search([('login', '=', values['login'])], limit=1)
            if user:
                default_group_ids = self._get_default_groups()
                if default_group_ids:
                    current_groups = user.groups_id.ids
                    groups_to_add = [gid for gid in default_group_ids if gid not in current_groups]
                    
                    if groups_to_add:
                        user.write({
                            'groups_id': [(4, group_id) for group_id in groups_to_add]
                        })
                        group_names = self.env['res.groups'].browse(groups_to_add).mapped('name')
                        _logger.info(f"Added default groups {group_names} to invited user {user.name} ({user.login})")
        
        return result