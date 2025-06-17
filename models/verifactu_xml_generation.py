import xml.etree.ElementTree as ET
import xml.sax.saxutils as saxutils
from odoo import models, fields, _
from odoo.exceptions import UserError
from xml.dom import minidom
import logging
from lxml import etree
import os
from decimal import Decimal, ROUND_HALF_UP

_logger = logging.getLogger(__name__)

class VeriFactuXMLGeneration(models.Model):
    _inherit = 'account.move'

    #Limpia el NIF del contacto ya sea compañía o empresa
    def _clean_vat(self, vat):
        if not vat:
            return ''
        cleaned = vat.replace(' ', '').replace('-', '').upper()
        if cleaned.startswith('ES'):
            cleaned = cleaned[2:]
        if len(cleaned) != 9:
            raise UserError(_("El NIF/CIF '%s' debe tener exactamente 9 caracteres después de limpiar.") % cleaned)
        return cleaned

    def _generate_verifactu_xml(self):
        self.ensure_one()
        invoice = self

        # Validación de impuestos 
        if not any(line.tax_ids for line in invoice.invoice_line_ids):
            raise UserError(_("La factura debe tener al menos un impuesto para poder enviarse a la AEAT (DetalleDesglose obligatorio)."))

        # Configuración de namespaces 
        namespaces = {
            'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
            'sum': 'https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroLR.xsd',
            'sum1': 'https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroInformacion.xsd',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
        }

        # Creación del envelope 
        envelope = ET.Element(
            'soapenv:Envelope',
            attrib={
                'xmlns:soapenv': namespaces['soapenv'],
                'xmlns:sum': namespaces['sum'],
                'xmlns:sum1': namespaces['sum1'],
                'xmlns:xsi': namespaces['xsi'],
                'xsi:schemaLocation': ' '.join([
                    namespaces['sum'], '/l10n_es_verifactu/static/xsd/SuministroLR.xsd',
                    namespaces['sum1'], '/l10n_es_verifactu/static/xsd/SuministroInformacion.xsd'
                ])
            }
        )

        # Cuerpo del XML 
        ET.SubElement(envelope, 'soapenv:Header')
        body = ET.SubElement(envelope, 'soapenv:Body')
        reg_factu = ET.SubElement(body, 'sum:RegFactuSistemaFacturacion')
        cabecera = ET.SubElement(reg_factu, 'sum:Cabecera')
        obligado_emision = ET.SubElement(cabecera, 'sum1:ObligadoEmision')
        ET.SubElement(obligado_emision, 'sum1:NombreRazon').text = saxutils.escape(invoice.company_id.name or '')
        ET.SubElement(obligado_emision, 'sum1:NIF').text = self._clean_vat(invoice.company_id.vat)

        registro_factura = ET.SubElement(reg_factu, 'sum:RegistroFactura')
        registro_alta = ET.SubElement(registro_factura, 'sum1:RegistroAlta')
        ET.SubElement(registro_alta, 'sum1:IDVersion').text = '1.0'

        # Sección IDFactura 
        id_factura = ET.SubElement(registro_alta, 'sum1:IDFactura')
        ET.SubElement(id_factura, 'sum1:IDEmisorFactura').text = self._clean_vat(invoice.company_id.vat)
        ET.SubElement(id_factura, 'sum1:NumSerieFactura').text = invoice.name
        ET.SubElement(id_factura, 'sum1:FechaExpedicionFactura').text = invoice.invoice_date.strftime('%d-%m-%Y')

        # Datos básicos 
        ET.SubElement(registro_alta, 'sum1:NombreRazonEmisor').text = saxutils.escape(invoice.company_id.name or '')
        ET.SubElement(registro_alta, 'sum1:TipoFactura').text = 'F1'
        description = ", ".join([line.name or '' for line in invoice.invoice_line_ids][:3])
        ET.SubElement(registro_alta, 'sum1:DescripcionOperacion').text = saxutils.escape(description[:500])

        # Destinatarios 
        destinatarios = ET.SubElement(registro_alta, 'sum1:Destinatarios')
        id_destinatario = ET.SubElement(destinatarios, 'sum1:IDDestinatario')
        ET.SubElement(id_destinatario, 'sum1:NombreRazon').text = saxutils.escape(invoice.partner_id.name or '')
        ET.SubElement(id_destinatario, 'sum1:NIF').text = self._clean_vat(invoice.partner_id.vat)

        # Desglose de impuestos 
        desglose = ET.SubElement(registro_alta, 'sum1:Desglose')
        total_cuota = Decimal('0.00')
        total_base = Decimal('0.00')

        for line in invoice.invoice_line_ids:
            base_imponible = Decimal(str(line.price_subtotal))
            total_base += base_imponible

            for tax in line.tax_ids:
                detalle = ET.SubElement(desglose, 'sum1:DetalleDesglose')
                ET.SubElement(detalle, 'sum1:ClaveRegimen').text = '01'
                ET.SubElement(detalle, 'sum1:CalificacionOperacion').text = 'S1'

                tipo_impositivo = Decimal(str(tax.amount))
                ET.SubElement(detalle, 'sum1:TipoImpositivo').text = f"{tipo_impositivo:.2f}"
                ET.SubElement(detalle, 'sum1:BaseImponibleOimporteNoSujeto').text = f"{base_imponible:.2f}"

                taxes = tax.compute_all(
                    line.price_unit,
                    line.currency_id,
                    line.quantity,
                    product=line.product_id,
                    partner=invoice.partner_id
                )

                try:
                    tax_amount = Decimal('0.00')
                    for t in taxes['taxes']:
                        if t['id'] == tax.id:
                            tax_amount += Decimal(str(t['amount']))
                    tax_amount = tax_amount.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                    total_cuota += tax_amount  # Sumamos al total
                except Exception as e:
                    _logger.warning("Error al calcular impuesto %s: %s", tax.name, str(e))
                    tax_amount = Decimal('0.00')

                ET.SubElement(detalle, 'sum1:CuotaRepercutida').text = f"{tax_amount:.2f}"

        
        ET.SubElement(registro_alta, 'sum1:CuotaTotal').text = f"{total_cuota:.2f}"
        ET.SubElement(registro_alta, 'sum1:ImporteTotal').text = f"{(total_base + total_cuota):.2f}"

        
        encadenamiento = ET.SubElement(registro_alta, 'sum1:Encadenamiento')
        registro_anterior = ET.SubElement(encadenamiento, 'sum1:RegistroAnterior')
        
        last_invoice = self.search([
            ('company_id', '=', invoice.company_id.id),
            ('verifactu_sent', '=', True),
            ('id', '!=', invoice.id)
        ], order='verifactu_sent_date desc', limit=1)

        if last_invoice:
            ET.SubElement(registro_anterior, 'sum1:IDEmisorFactura').text = self._clean_vat(last_invoice.company_id.vat)
            ET.SubElement(registro_anterior, 'sum1:NumSerieFactura').text = last_invoice.name
            ET.SubElement(registro_anterior, 'sum1:FechaExpedicionFactura').text = last_invoice.invoice_date.strftime('%d-%m-%Y')
            ET.SubElement(registro_anterior, 'sum1:Huella').text = last_invoice.verifactu_hash or ''
        else:
            ET.SubElement(registro_anterior, 'sum1:IDEmisorFactura').text = self._clean_vat(invoice.company_id.vat)
            ET.SubElement(registro_anterior, 'sum1:NumSerieFactura').text = 'INITIAL'
            ET.SubElement(registro_anterior, 'sum1:FechaExpedicionFactura').text = invoice.invoice_date.strftime('%d-%m-%Y')
            ET.SubElement(registro_anterior, 'sum1:Huella').text = 'INITIAL'

        # Resto de elementos 
        sistema = ET.SubElement(registro_alta, 'sum1:SistemaInformatico')
        ET.SubElement(sistema, 'sum1:NombreRazon').text = saxutils.escape('Odoo')
        ET.SubElement(sistema, 'sum1:NIF').text = self._clean_vat(invoice.company_id.vat)
        ET.SubElement(sistema, 'sum1:NombreSistemaInformatico').text = 'Odoo VeriFactu'
        ET.SubElement(sistema, 'sum1:IdSistemaInformatico').text = 'OD'
        ET.SubElement(sistema, 'sum1:Version').text = '1.0.03'
        ET.SubElement(sistema, 'sum1:NumeroInstalacion').text = str(invoice.company_id.id)
        ET.SubElement(sistema, 'sum1:TipoUsoPosibleSoloVerifactu').text = 'N'
        ET.SubElement(sistema, 'sum1:TipoUsoPosibleMultiOT').text = 'S'
        ET.SubElement(sistema, 'sum1:IndicadorMultiplesOT').text = 'S'

        ET.SubElement(registro_alta, 'sum1:FechaHoraHusoGenRegistro').text = fields.Datetime.now().strftime('%Y-%m-%dT%H:%M:%S+01:00')
        ET.SubElement(registro_alta, 'sum1:TipoHuella').text = '01'
        ET.SubElement(registro_alta, 'sum1:Huella').text = invoice.verifactu_hash or ''

        # Generación del XML 
        xml_str = ET.tostring(envelope, encoding='utf-8', method='xml')
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')

        # Firma del XML 
        try:
            cert_pem = invoice.company_id.verifactu_cert_pem
            key_pem = invoice.company_id.verifactu_key_pem
            key_pass = invoice.company_id.verifactu_key_password

            if not cert_pem or not key_pem:
                raise UserError(_("Certificado o clave privada no configurados en los ajustes de la empresa."))

            signature_record = self.env['verifactu.signature'].search([('move_id', '=', invoice.id)], limit=1)
            if not signature_record:
                signature_record = self.env['verifactu.signature'].create({
                    'move_id': invoice.id,
                })

            signed_xml = signature_record._sign_verifactu_xml(
                xml_str=pretty_xml,
                cert_pem=cert_pem,
                key_pem=key_pem,
                key_pass=key_pass,
            )
            return signed_xml

        except Exception as e:
            _logger.error("Error al firmar o validar el XML: %s", str(e))
            raise UserError(_("Error al firmar o validar el XML para VeriFactu: %s") % str(e))


    def _validate_xml_against_schema(self, xml_data):
        self.ensure_one()
        xsd_path = self.env['ir.config_parameter'].sudo().get_param('verifactu.xsd_path')
        if not xsd_path or not os.path.isfile(xsd_path):
            raise UserError("No se encontró el archivo de esquema XSD de VeriFactu. Verifica la ruta en la configuración.")
        
        try:
            # Parseamos todo el XML
            xml_doc = etree.fromstring(xml_data.encode('utf-8'))

            # Extraemos el cuerpo del mensaje SOAP 
            body = xml_doc.find('.//soapenv:Body', namespaces=xml_doc.nsmap)

            if body is None:
                raise UserError("No se encontró el elemento <soapenv:Body> en el XML.")

            # Tomamos el primer hijo del Body (por ejemplo, sum:RegFactuSistemaFacturacion)
            root_element_to_validate = body[0]

            # Convertimos a cadena ese fragmento
            xml_fragment = etree.tostring(root_element_to_validate, encoding='utf-8')

            # Parseamos el XSD
            xsd_doc = etree.parse(xsd_path)
            schema = etree.XMLSchema(xsd_doc)

            # Validamos solo el fragmento
            xml_to_validate = etree.fromstring(xml_fragment)
            if not schema.validate(xml_to_validate):
                errors = "\n".join([str(e) for e in schema.error_log])
                raise UserError(f"El XML no es válido según el esquema XSD:\n{errors}")

            return True
        except Exception as e:
            raise UserError(f"Error durante la validación del XML: {str(e)}")