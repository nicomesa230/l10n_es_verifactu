import hashlib
from odoo import models, fields

class VeriFactuHash(models.Model):
    _inherit = 'account.move'

    # Limpia el VAT y genera un hash único para la factura
    def _clean_vat(self, vat):
        if not vat:
            return ''
        return ''.join(filter(str.isalnum, vat)).upper().lstrip('ES')

    # Genera un hash único para la factura según especificaciones AEAT
    def _generate_verifactu_hash(self):
        for invoice in self:
            name = invoice.name or 'NO-NUMBER'
            date = invoice.invoice_date.strftime('%d-%m-%Y') if invoice.invoice_date else 'NO-DATE'
            company_vat = self._clean_vat(invoice.company_id.vat) or 'NO-COMPANY-VAT'
            partner_vat = self._clean_vat(invoice.partner_id.vat) or 'NO-PARTNER-VAT'
            timestamp = fields.Datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

            data = (
                f"{name}|"
                f"{date}|"
                f"{company_vat}|"
                f"{partner_vat}|"
                f"{invoice.amount_total:.2f}|"
                f"{timestamp}"
            )
            hash_object = hashlib.sha256(data.encode("utf-8"))
            invoice.verifactu_hash = hash_object.hexdigest()
