# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request, Response
from odoo.exceptions import AccessError


class PayslipController(http.Controller):

    @http.route('/payslip/download/<int:attachment_id>/<string:access_token>', type='http', auth='public', website=True)
    def download_payslip(self, attachment_id, access_token, **kwargs):
        """
        Public route to download payslip PDF with access token
        No login required - validates via token
        """
        import logging
        _logger = logging.getLogger(__name__)

        try:
            _logger.info(f'Download request: attachment_id={attachment_id}, token={access_token}')

            # Search for attachment with matching ID and token
            attachment = request.env['ir.attachment'].sudo().search([
                ('id', '=', attachment_id),
                ('access_token', '=', access_token),
            ], limit=1)

            if not attachment:
                _logger.warning(f'Attachment not found: id={attachment_id}, token={access_token}')
                return Response(
                    'Invalid or expired download link.',
                    status=404,
                    content_type='text/plain'
                )

            # Check if attachment is a payslip
            if attachment.res_model != 'vn.payslip':
                _logger.warning(f'Invalid model: {attachment.res_model}, expected vn.payslip')
                return Response(
                    'Invalid payslip document.',
                    status=403,
                    content_type='text/plain'
                )

            # Get file content - use raw if available, otherwise decode datas
            file_content = None
            if hasattr(attachment, 'raw') and attachment.raw:
                _logger.info('Using attachment.raw')
                file_content = attachment.raw
            elif attachment.datas:
                _logger.info('Using attachment.datas (base64 decoded)')
                import base64
                file_content = base64.b64decode(attachment.datas)
            else:
                _logger.error('No file content found in attachment')
                return Response(
                    'Payslip file not found.',
                    status=404,
                    content_type='text/plain'
                )

            _logger.info(f'Returning PDF file: {attachment.name}, size: {len(file_content)} bytes')

            # Encode filename for HTTP header (handle Vietnamese characters)
            import urllib.parse
            encoded_filename = urllib.parse.quote(attachment.name)

            # Return PDF file
            return request.make_response(
                file_content,
                headers=[
                    ('Content-Type', attachment.mimetype or 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename*=UTF-8\'\'{encoded_filename}'),
                    ('Content-Length', len(file_content)),
                ]
            )

        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error('Error downloading payslip: %s', str(e), exc_info=True)
            return Response(
                f'Error downloading payslip: {str(e)}',
                status=500,
                content_type='text/plain'
            )

    @http.route('/vn_hr_payroll/template_preview', type='http', auth='user', website=True)
    def template_preview(self, preview_id=None, **kwargs):
        """
        Preview route for email templates
        Displays rendered HTML template in a clean layout
        Uses session storage to avoid URL length issues
        """
        html = '<p style="color: #999; text-align: center; padding: 50px;">No template content to preview.</p>'

        if preview_id:
            # Get HTML from session
            session_key = f'template_preview_{preview_id}'
            html = request.session.get(session_key, html)
            # Clean up session after reading
            if session_key in request.session:
                del request.session[session_key]

        # Return HTML wrapped in basic structure
        return request.make_response(
            f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Template Preview</title>
                <style>
                    body {{
                        margin: 0;
                        padding: 20px;
                        font-family: Arial, sans-serif;
                        background-color: #f5f5f5;
                    }}
                    .preview-container {{
                        max-width: 800px;
                        margin: 0 auto;
                        background-color: white;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        padding: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="preview-container">
                    {html}
                </div>
            </body>
            </html>
            """,
            headers=[
                ('Content-Type', 'text/html; charset=utf-8'),
            ]
        )
