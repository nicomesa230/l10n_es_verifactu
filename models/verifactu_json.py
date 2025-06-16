from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import json

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _generate_verifactu_json(self):
        """
        Genera un diccionario con los datos de la factura en formato compatible
        con el esquema de VeriFactu de la AEAT.
        """
        self.ensure_one()
        invoice = self  

        # Validar impuestos
        if not any(line.tax_ids for line in invoice.invoice_line_ids):
            raise UserError("La factura debe tener al menos un impuesto para poder enviarse a la AEAT.")

        # Cabecera - ObligadoEmision
        obligado_emision = {
            "NombreRazon": invoice.company_id.name or "",
            "NIF": self._clean_vat(invoice.company_id.vat),
        }

        # RegistroAlta - IDFactura
        id_factura = {
            "IDEmisorFactura": self._clean_vat(invoice.company_id.vat),
            "NumSerieFactura": invoice.name,
            "FechaExpedicionFactura": invoice.invoice_date.strftime('%d-%m-%Y'),
        }

        # Descripción operación
        description = "Factura de venta"
        if invoice.invoice_line_ids:
            description = ", ".join([line.name or '' for line in invoice.invoice_line_ids][:3])
        description = description[:500]

        # Destinatarios
        destinatarios = {
            "IDDestinatario": {
                "NombreRazon": invoice.partner_id.name or "",
                "NIF": self._clean_vat(invoice.partner_id.vat),
            }
        }

        # Desglose de impuestos
        desglose = []
        for line in invoice.invoice_line_ids:
            if not line.tax_ids:
                continue
            for tax in line.tax_ids:
                taxes = tax.compute_all(
                    line.price_unit, line.currency_id, line.quantity,
                    product=line.product_id, partner=invoice.partner_id
                )
                tax_amount = sum(t['amount'] for t in taxes['taxes'] if abs(t['amount']) > 0)

                detalle = {
                    "ClaveRegimen": "01",  # Régimen general
                    "CalificacionOperacion": "S1",  # Sujeto pasivo
                    "TipoImpositivo": f"{tax.amount:.2f}",
                    "BaseImponibleOimporteNoSujeto": f"{line.price_subtotal:.2f}",
                    "CuotaRepercutida": f"{tax_amount:.2f}"
                }
                desglose.append(detalle)

        # Encadenamiento
        last_invoice = self.search([
            ('company_id', '=', invoice.company_id.id),
            ('verifactu_sent', '=', True),
            ('id', '!=', invoice.id)
        ], order='verifactu_sent_date desc', limit=1)

        registro_anterior = {}
        if last_invoice:
            registro_anterior = {
                "IDEmisorFactura": self._clean_vat(last_invoice.company_id.vat),
                "NumSerieFactura": last_invoice.name,
                "FechaExpedicionFactura": last_invoice.invoice_date.strftime('%d-%m-%Y'),
                "Huella": last_invoice.verifactu_hash or ""
            }
        else:
            registro_anterior = {
                "IDEmisorFactura": self._clean_vat(invoice.company_id.vat),
                "NumSerieFactura": "INITIAL",
                "FechaExpedicionFactura": invoice.invoice_date.strftime('%d-%m-%Y'),
                "Huella": "INITIAL"
            }

        # Sistema informático
        sistema_informatico = {
            "NombreRazon": "Odoo",
            "NIF": self._clean_vat(invoice.company_id.vat),
            "NombreSistemaInformatico": "Odoo VeriFactu",
            "IdSistemaInformatico": "OD",
            "Version": "1.0.03",
            "NumeroInstalacion": str(invoice.company_id.id),
            "TipoUsoPosibleSoloVerifactu": "N",
            "TipoUsoPosibleMultiOT": "S",
            "IndicadorMultiplesOT": "S"
        }

        # RegistroAlta completo
        registro_alta = {
            "IDVersion": "1.0",
            "IDFactura": id_factura,
            "NombreRazonEmisor": invoice.company_id.name or "",
            "TipoFactura": "F1",
            "DescripcionOperacion": description,
            "Destinatarios": destinatarios,
            "Desglose": desglose,
            "CuotaTotal": f"{invoice.amount_tax:.2f}",
            "ImporteTotal": f"{invoice.amount_total:.2f}",
            "Subsanacion": "S" if invoice.verifactu_subsanacion else None,
            "RechazoPrevio": "X" if invoice.verifactu_rechazo_previo else None,
            "Encadenamiento": {
                "RegistroAnterior": registro_anterior
            },
            "SistemaInformatico": sistema_informatico,
            "FechaHoraHusoGenRegistro": fields.Datetime.now().strftime('%Y-%m-%dT%H:%M:%S+01:00'),
            "TipoHuella": "01",
            "Huella": invoice.verifactu_hash or ""
        }

        # Devolver resultado
        result = {
            "Cabecera": {
                "ObligadoEmision": obligado_emision
            },
            "RegistroFactura": {
                "RegistroAlta": registro_alta
            }
        }

        return result  

    def action_download_verifactu_json(self):
        """
        Acción que permite descargar el JSON generado en un archivo.
        """
        self.ensure_one()
        json_data = self._generate_verifactu_json()

        json_content = json.dumps(json_data, indent=4, ensure_ascii=False)
        json_base64 = base64.b64encode(json_content.encode('utf-8'))

        attachment = self.env['ir.attachment'].create({
            'name': f'verifactu_{self.name}.json',
            'type': 'binary',
            'datas': json_base64,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/json'
        })

        download_url = f'/web/content/{attachment.id}?download=true'
        return {
            'type': 'ir.actions.act_url',
            'url': download_url,
            'target': 'self',
        }