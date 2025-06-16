import qrcode
from io import BytesIO
import base64
from odoo import models

class VeriFactuQR(models.Model):
    _inherit = 'account.move'

    # Genera un código QR con los datos de la factura
    def _generate_verifactu_qr(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for invoice in self:
            if not invoice.verifactu_hash:
                continue
            qr_url = f"{base_url}/verifactu/scan/{invoice.verifactu_hash}"
            qr = qrcode.make(qr_url)
            buffer = BytesIO()
            qr.save(buffer, format="PNG")
            invoice.verifactu_qr = base64.b64encode(buffer.getvalue())