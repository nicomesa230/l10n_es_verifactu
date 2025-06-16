import xml.etree.ElementTree as ET
import xml.sax.saxutils as saxutils
from odoo import models, fields, _
from xml.dom import minidom
from odoo.exceptions import UserError
import os
from lxml import etree

class VeriFactuXMLGeneration(models.Model):
    _inherit = 'account.move'

    #Genera el XML para VeriFactu según el esquema definido por la AEAT
    def _generate_verifactu_xml(self):
        self.ensure_one()
        import xml.sax.saxutils as saxutils
        for invoice in self:
            # Validar que haya al menos un impuesto
            if not any(line.tax_ids for line in invoice.invoice_line_ids):
                raise UserError("La factura debe tener al menos un impuesto para poder enviarse a la AEAT (DetalleDesglose obligatorio).")
            namespaces = {
                        'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
                        'sum': 'https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroLR.xsd',
                        'sum1': 'https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroInformacion.xsd',
                        'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
                    }
            
            schema_locations = [
                'http://schemas.xmlsoap.org/soap/envelope/',
                'http://schemas.xmlsoap.org/soap/envelope/',
                namespaces['sum'],
                '/l10n_es_verifactu/static/xsd/SuministroLR.xsd',  
                namespaces['sum1'],
                '/l10n_es_verifactu/static/xsd/SuministroInformacion.xsd'  
            ]

            envelope = ET.Element(
                'soapenv:Envelope',
                attrib={
                    'xmlns:soapenv': namespaces['soapenv'],
                    'xmlns:sum': namespaces['sum'],
                    'xmlns:sum1': namespaces['sum1'],
                    'xmlns:xsi': namespaces['xsi'],
                    'xsi:schemaLocation': ' '.join(schema_locations)
                }
            )
            header = ET.SubElement(envelope, 'soapenv:Header')
            body = ET.SubElement(envelope, 'soapenv:Body')
            
            reg_factu = ET.SubElement(body, 'sum:RegFactuSistemaFacturacion')
            cabecera = ET.SubElement(reg_factu, 'sum:Cabecera')
            obligado_emision = ET.SubElement(cabecera, 'sum1:ObligadoEmision')
            ET.SubElement(obligado_emision, 'sum1:NombreRazon').text = saxutils.escape(invoice.company_id.name or '')
            ET.SubElement(obligado_emision, 'sum1:NIF').text = self._clean_vat(invoice.company_id.vat)
            
            # Registro Factura
            registro_factura = ET.SubElement(reg_factu, 'sum:RegistroFactura')
            registro_alta = ET.SubElement(registro_factura, 'sum1:RegistroAlta')
            
            # IDVersion
            ET.SubElement(registro_alta, 'sum1:IDVersion').text = '1.0'
            
            # IDFactura
            id_factura = ET.SubElement(registro_alta, 'sum1:IDFactura')
            ET.SubElement(id_factura, 'sum1:IDEmisorFactura').text = self._clean_vat(invoice.company_id.vat)
            ET.SubElement(id_factura, 'sum1:NumSerieFactura').text = invoice.name
            ET.SubElement(id_factura, 'sum1:FechaExpedicionFactura').text = invoice.invoice_date.strftime('%d-%m-%Y')
            
            # Datos de la factura
            ET.SubElement(registro_alta, 'sum1:NombreRazonEmisor').text = saxutils.escape(invoice.company_id.name or '')
            ET.SubElement(registro_alta, 'sum1:TipoFactura').text = 'F1'  # Factura completa
            
            # Descripción operación
            description = "Factura de venta"
            if invoice.invoice_line_ids:
                description = ", ".join([line.name or '' for line in invoice.invoice_line_ids][:3])
            ET.SubElement(registro_alta, 'sum1:DescripcionOperacion').text = saxutils.escape(description[:500])

            
            # Destinatarios
            destinatarios = ET.SubElement(registro_alta, 'sum1:Destinatarios')
            id_destinatario = ET.SubElement(destinatarios, 'sum1:IDDestinatario')
            ET.SubElement(id_destinatario, 'sum1:NombreRazon').text = saxutils.escape(invoice.partner_id.name or '')
            ET.SubElement(id_destinatario, 'sum1:NIF').text = self._clean_vat(invoice.partner_id.vat)
            
            # Desglose de impuestos
            desglose = ET.SubElement(registro_alta, 'sum1:Desglose')
            
            for line in invoice.invoice_line_ids:
                if not line.tax_ids:
                    continue
                    
                for tax in line.tax_ids:
                    detalle = ET.SubElement(desglose, 'sum1:DetalleDesglose')
                    ET.SubElement(detalle, 'sum1:ClaveRegimen').text = '01'  # Régimen general
                    ET.SubElement(detalle, 'sum1:CalificacionOperacion').text = 'S1'  # Sujeto pasivo
                    ET.SubElement(detalle, 'sum1:TipoImpositivo').text = f"{tax.amount:.2f}"
                    ET.SubElement(detalle, 'sum1:BaseImponibleOimporteNoSujeto').text = f"{line.price_subtotal:.2f}"
                    # Calcular el impuesto de la línea para ese impuesto
                    tax_amount = 0.0
                    taxes = tax.compute_all(line.price_unit, line.currency_id, line.quantity, product=line.product_id, partner=line.move_id.partner_id)
                    for t in taxes['taxes']:
                        if abs(t['amount']) > 0:  # Puedes ajustar el filtro si hay varios impuestos
                            tax_amount += t['amount']
                    ET.SubElement(detalle, 'sum1:CuotaRepercutida').text = f"{tax_amount:.2f}"
            
            # Totales
            ET.SubElement(registro_alta, 'sum1:CuotaTotal').text = f"{invoice.amount_tax:.2f}"
            ET.SubElement(registro_alta, 'sum1:ImporteTotal').text = f"{invoice.amount_total:.2f}"
            # Subsanación y rechazo previo si aplica
            if invoice.verifactu_subsanacion:
                ET.SubElement(registro_alta, 'sum1:Subsanacion').text = 'S'
            if invoice.verifactu_rechazo_previo:
                ET.SubElement(registro_alta, 'sum1:RechazoPrevio').text = 'X'

            # Encadenamiento (hash de la factura anterior)
            encadenamiento = ET.SubElement(registro_alta, 'sum1:Encadenamiento')
            registro_anterior = ET.SubElement(encadenamiento, 'sum1:RegistroAnterior')
            
            # Buscar última factura enviada
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
                # Primera factura
                ET.SubElement(registro_anterior, 'sum1:IDEmisorFactura').text = self._clean_vat(invoice.company_id.vat)
                ET.SubElement(registro_anterior, 'sum1:NumSerieFactura').text = 'INITIAL'
                ET.SubElement(registro_anterior, 'sum1:FechaExpedicionFactura').text = invoice.invoice_date.strftime('%d-%m-%Y')
                ET.SubElement(registro_anterior, 'sum1:Huella').text = 'INITIAL'
            
            # Sistema informático
            sistema = ET.SubElement(registro_alta, 'sum1:SistemaInformatico')
            ET.SubElement(sistema, 'sum1:NombreRazon').text = saxutils.escape('Odoo')
            ET.SubElement(sistema, 'sum1:NIF').text = self._clean_vat(invoice.company_id.vat)
            ET.SubElement(sistema, 'sum1:NombreSistemaInformatico').text = saxutils.escape('Odoo VeriFactu')
            ET.SubElement(sistema, 'sum1:IdSistemaInformatico').text = 'OD'
            ET.SubElement(sistema, 'sum1:Version').text = '1.0.03'
            ET.SubElement(sistema, 'sum1:NumeroInstalacion').text = str(invoice.company_id.id)
            ET.SubElement(sistema, 'sum1:TipoUsoPosibleSoloVerifactu').text = 'N'
            ET.SubElement(sistema, 'sum1:TipoUsoPosibleMultiOT').text = 'S'
            ET.SubElement(sistema, 'sum1:IndicadorMultiplesOT').text = 'S'

            
            # Fecha y huella
            ET.SubElement(registro_alta, 'sum1:FechaHoraHusoGenRegistro').text = fields.Datetime.now().strftime('%Y-%m-%dT%H:%M:%S+01:00')
            ET.SubElement(registro_alta, 'sum1:TipoHuella').text = '01'  
            ET.SubElement(registro_alta, 'sum1:Huella').text = invoice.verifactu_hash or ''
            
            # Convertir a XML string con formato
            xml_str = ET.tostring(envelope, encoding='utf-8', method='xml')
            dom = minidom.parseString(xml_str)
            pretty_xml = dom.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')
            
            return pretty_xml

    def _validate_xml_against_schema(self, xml_data):
        self.ensure_one()
        xsd_path = self.env['ir.config_parameter'].sudo().get_param('verifactu.xsd_path')
        if not xsd_path or not os.path.isfile(xsd_path):
            raise UserError("No se encontró el archivo de esquema XSD de VeriFactu. Verifica la ruta en la configuración.")
        
        try:
            # Parseamos todo el XML
            xml_doc = etree.fromstring(xml_data.encode('utf-8'))

            # Extraemos el cuerpo del mensaje SOAP (lo importante para validación)
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