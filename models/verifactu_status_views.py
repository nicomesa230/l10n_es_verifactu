from odoo import models, fields, _
from odoo.exceptions import UserError
import os
from lxml import etree

class VeriFactuStatusViews(models.Model):
    _inherit = 'account.move'

    # Campos para almacenar el estado y respuesta de VeriFactu
    def action_send_verifactu(self):
        for invoice in self:
            if invoice.verifactu_state == 'accepted':
                continue

            missing_fields = []
            if not invoice.name: missing_fields.append("Número de factura")
            if not invoice.invoice_date: missing_fields.append("Fecha de factura")
            if not invoice.partner_id.vat: missing_fields.append("NIF del cliente")
            if not invoice.company_id.vat: missing_fields.append("NIF de la empresa")
            if missing_fields:
                raise UserError(_("Faltan campos requeridos:\n") + "\n".join(missing_fields))

            invoice._generate_verifactu_hash()
            xml_data = invoice._generate_verifactu_xml()
            invoice.verifactu_xml = xml_data
            invoice._validate_xml_against_schema(xml_data)
            invoice._generate_verifactu_qr()

            result = invoice._send_to_aeat(xml_data)
            if result.get('success'):
                parsed = invoice._parse_aeat_response(result.get('response', ''))
                estado = parsed.get('estado', 'error').lower()
                mapping = {
                    'aceptado': 'accepted',
                    'aceptado parcialmente': 'partially_accepted',
                    'rechazado': 'rejected',
                    'error': 'error'
                }
                invoice.verifactu_state = mapping.get(estado, 'error')
                invoice.verifactu_sent = True
                invoice.verifactu_sent_date = fields.Datetime.now()
                invoice.verifactu_csv = parsed.get('csv', '')
                invoice.verifactu_response = result.get('response', '')
            else:
                invoice.verifactu_state = 'error'
                invoice.verifactu_response = result.get('error', '')

    # Acción para ver el estado de VeriFactu
    def action_view_verifactu_status(self):
        self.ensure_one()
        if not self.verifactu_sent:
            raise UserError(_("La factura aún no ha sido enviada a la AEAT."))
        msg = f"<b>Estado AEAT:</b> {self.verifactu_state.upper()}<br/>..."
        return {
            'type': 'ir.actions.act_window',
            'name': 'Estado AEAT',
            'res_model': 'account.move',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'views': [(False, 'form')],
            'context': self.env.context,
            'effect': {
                'fadeout': 'slow',
                'message': 'Estado cargado correctamente',
                'type': 'rainbow_man'
            },
            'warning': {
                'title': f"Estado AEAT: {self.verifactu_state.upper()}",
                'message': msg,
            },
        }