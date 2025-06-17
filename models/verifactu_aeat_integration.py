import requests
import xml.etree.ElementTree as ET
import tempfile
import os
from odoo import models, fields, _
from odoo.exceptions import UserError


class VeriFactuAEATIntegration(models.Model):
    _inherit = 'account.move'

    def _send_to_aeat(self, xml_data):
        company = self.env.company
        cert_pem = company.verifactu_cert_pem
        key_pem = company.verifactu_key_pem
        key_password = company.verifactu_key_password

        # Validación para el certificado y la clave
        if not cert_pem or not key_pem:
            return {
                'success': False,
                'error': _('Faltan el certificado o la clave privada.'),
                'status_code': 400
            }

        # Crear archivos temporales para certificado y clave
        try:
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.pem', delete=False) as cert_file:
                cert_file.write(cert_pem)
                cert_file.flush()
                cert_path = cert_file.name

            with tempfile.NamedTemporaryFile(mode='w+', suffix='.pem', delete=False) as key_file:
                key_file.write(key_pem)
                key_file.flush()
                key_path = key_file.name

            config = self.env['ir.config_parameter'].sudo()
            test_mode = config.get_param('verifactu.test_mode', default=True)

            wsdl_url = 'https://prewww1.aeat.es/wbWTINE-CONT/swi/SistemaFacturacion/VerifactuSOAP'  if test_mode else 'https://www1.agenciatributaria.gob.es/wbWTINE-CONT/swi/SistemaFacturacion/VerifactuSOAP' 

            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/RegFactuSistemaFacturacion' 
            }

            # Enviar solicitud con certificado y clave temporales
            response = requests.post(
                wsdl_url,
                data=xml_data,
                headers=headers,
                cert=(cert_path, key_path),
                timeout=30
            )

            # Limpiar archivos temporales
            os.unlink(cert_path)
            os.unlink(key_path)

            if response.status_code == 403:
                return {
                    'success': False,
                    'error': _('Error 403: No se detecta certificado válido o no se seleccionó correctamente.'),
                    'status_code': 403
                }

            return {
                'success': True,
                'response': response.text,
                'status_code': response.status_code
            }

        except requests.exceptions.SSLError as e:
            return {
                'success': False,
                'error': _('Error SSL: Certificado inválido o no reconocido.'),
                'status_code': 403
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': _('No se pudo conectar con el servidor de la AEAT. Verifique su conexión a internet.'),
                'status_code': 503
            }
        except Exception as e:
            return {
                'success': False,
                'error': _('Error al enviar el documento: %s') % str(e),
                'status_code': 500
            }

    def _parse_aeat_response(self, xml_response):
            try:
                root = ET.fromstring(xml_response)
                namespaces = {
                    'resp': 'https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/RespuestaSuministro.xsd' 
                }
                
                # Extraer información básica de la respuesta
                estado_envio = root.find('.//resp:EstadoEnvio', namespaces)
                csv = root.find('.//resp:CSV', namespaces)
                errores = root.findall('.//resp:Error', namespaces)
                
                estado = estado_envio.text if estado_envio is not None else 'Error'
                csv_text = csv.text if csv is not None else ''
                
                # Procesar errores si existen
                error_messages = []
                if errores:
                    for error in errores:
                        codigo = error.find('resp:Codigo', namespaces)
                        descripcion = error.find('resp:Descripcion', namespaces)
                        if codigo is not None and descripcion is not None:
                            error_messages.append(
                                f"Código de error: {codigo.text}. Descripción: {descripcion.text}"
                            )
                
                result = {
                    'estado': estado,
                    'csv': csv_text,
                    'errores': error_messages if error_messages else None
                }
                
                # Si hay errores pero el estado no es Error, actualizamos el estado
                if error_messages and estado != 'Error':
                    result['estado'] = 'Error'
                
                return result
                
            except ET.ParseError as e:
                return {
                    'estado': 'Error',
                    'csv': '',
                    'errores': ['La respuesta recibida no es un XML válido. Por favor, contacte con soporte técnico.']
                }
            except Exception as e:
                return {
                    'estado': 'Error',
                    'csv': '',
                    'errores': [f'Ocurrió un error inesperado al procesar la respuesta: {str(e)}. Por favor, inténtelo de nuevo más tarde.']
                }