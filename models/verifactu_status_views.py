from odoo import models, fields, _
from odoo.exceptions import UserError
import os
from lxml import etree
import html

class VeriFactuStatusViews(models.Model):
    _inherit = 'account.move'

    # Campos para almacenar el estado y respuesta de VeriFactu
    def action_send_verifactu(self):

        for invoice in self:

            if invoice.state != 'posted':
                raise UserError(_(
                    "❌ No puedes enviar esta factura a la AEAT porque no ha sido confirmada.\n\n"
                    "Posibles causas:\n"
                    "1. La factura está en estado 'Borrador'\n"
                    "2. La factura ha sido cancelada\n\n"
                    "✅ Solución:\n"
                    "Asegúrate de que la factura esté en estado 'Confirmada' antes de enviarla."
                ))

            if invoice.verifactu_state in ['accepted', 'partially_accepted']:
                raise UserError(_("Esta factura ya fue enviada a la AEAT y aceptada. No es posible reenviarla."))

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
            raise UserError(_(
                "❌ No puedes revisar el estado de la AEAT\n\n"
                "Posibles causas:\n"
                "1. La factura está en estado 'Borrador'\n"
                "2. La factura ha sido cancelada\n"
                "3. No accionaste el botón enviar AEAT\n\n"
                "✅ Solución:\n"
                "Asegúrate de que la factura esté en estado 'Confirmada' y después acciona el botón enviar AEAT para revisar el estado de esta factura en vivo."
            ))

        wizard = self.env['verifactu.status.wizard'].create({
            'status': self.verifactu_state,
            'sent_date': self.verifactu_sent_date,
        })
        wizard.set_response(self.verifactu_response or "No contestado")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Estado del envío a la AEAT',
            'res_model': 'verifactu.status.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }