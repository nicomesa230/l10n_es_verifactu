import requests
import xml.etree.ElementTree as ET
from odoo import models, _

class VeriFactuAEATIntegration(models.Model):
    _inherit = 'account.move'

    # Envía el XML generado a la AEAT y procesa la respuesta
    def _send_to_aeat(self, xml_data):
        config = self.env['ir.config_parameter'].sudo()
        test_mode = config.get_param('verifactu.test_mode', default=True)
        wsdl_url = 'https://prewww1.aeat.es/wbWTINE-CONT/swi/SistemaFacturacion/VerifactuSOAP'  if test_mode else 'https://www1.agenciatributaria.gob.es/wbWTINE-CONT/swi/SistemaFacturacion/VerifactuSOAP' 

        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/RegFactuSistemaFacturacion' 
        }

        try:
            response = requests.post(
                wsdl_url,
                data=xml_data,
                headers=headers,
                cert=(config.get_param('verifactu.cert_path'), config.get_param('verifactu.key_path')),
                timeout=30
            )
            return {'success': True, 'response': response.text, 'status_code': response.status_code}
        except Exception as e:
            return {'success': False, 'error': str(e), 'status_code': 500}

    # Procesa la respuesta de la AEAT y devuelve el estado y CSV
    def _parse_aeat_response(self, xml_response):
        try:
            root = ET.fromstring(xml_response)
            namespaces = {
                'resp': 'https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/RespuestaSuministro.xsd' 
            }
            estado_envio = root.find('.//resp:EstadoEnvio', namespaces)
            estado = estado_envio.text if estado_envio is not None else 'Error'
            csv = root.find('.//resp:CSV', namespaces)
            csv_text = csv.text if csv is not None else ''
            return {'estado': estado, 'csv': csv_text}
        except ET.ParseError as e:
            return {'estado': 'Error', 'csv': '', 'error': str(e)}