from odoo import models, fields
from odoo.exceptions import UserError
from lxml import etree as ET
from signxml import XMLSigner, methods
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.backends import default_backend
import base64
import logging

_logger = logging.getLogger(__name__)


class VeriFactuSignature(models.Model):
    _name = 'verifactu.signature'
    _description = 'Firma Electrónica VeriFactu'
    _order = 'create_date desc'

    move_id = fields.Many2one('account.move', string='Factura', required=True, ondelete='cascade', index=True)

    verifactu_signature_value = fields.Text("Firma XML", readonly=True)
    verifactu_signature_date = fields.Datetime("Fecha de Firma", readonly=True)
    verifactu_x509_certificate = fields.Text("Certificado X.509", readonly=True)
    verifactu_digest_value = fields.Char("Digest Value", readonly=True)
    verifactu_signature_algorithm = fields.Char("Algoritmo de Firma", readonly=True)
    verifactu_signed_info = fields.Text("SignedInfo XML", readonly=True)
    verifactu_reference_uri = fields.Char("Referencia URI", readonly=True)

    def _sign_verifactu_xml(self, xml_str, cert_pem, key_pem, key_pass=None, reference_uri=None):
        _logger.info("Iniciando proceso de firma VeriFactu...")

        # Validación de datos de entrada con mensajes claros
        if not xml_str:
            raise UserError("❌ No se proporcionó el XML para firmar. Por favor, genere primero el XML de la factura.")
        
        if not cert_pem:
            raise UserError("❌ No se encontró el certificado digital. Configure el certificado en los ajustes de la empresa.")
            
        if not key_pem:
            raise UserError("❌ No se encontró la clave privada. Configure la clave privada en los ajustes de la empresa.")

        # Cargar clave privada con manejo de errores detallado
        try:
            private_key = load_pem_private_key(
                key_pem.encode(),
                password=key_pass.encode() if key_pass else None,
                backend=default_backend()
            )
            _logger.info("Clave privada cargada correctamente.")
        except ValueError as e:
            if "Could not deserialize key data" in str(e):
                raise UserError("🔑 Error en la clave privada: El formato no es válido o la contraseña es incorrecta.")
            raise UserError(f"🔑 Error al procesar la clave privada: {str(e)}")
        except Exception as e:
            _logger.exception("Error técnico al cargar la clave privada")
            raise UserError("🔑 Ocurrió un problema técnico al procesar la clave privada. Contacte al administrador.")

        # Parsear XML con validación clara
        try:
            doc = ET.fromstring(xml_str.encode('utf-8'))
            _logger.info("XML parseado correctamente.")
        except ET.XMLSyntaxError as e:
            error_msg = f"""
            ❌ El XML generado no es válido:
            
            Error: {str(e)}
            
            Por favor:
            1. Verifique que la factura tenga todos los datos requeridos
            2. Contacte al soporte técnico si el problema persiste
            """
            raise UserError(error_msg)

        # Configurar firmador
        try:
            signer = XMLSigner(
                method=methods.enveloped,
                signature_algorithm="rsa-sha256",
                digest_algorithm="sha256",
                c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
            )
            _logger.info("Firmador XMLSigner configurado.")
        except Exception as e:
            raise UserError(f"⚙️ Error al configurar el sistema de firma: {str(e)}")

        # Firmar documento con mensajes detallados
        try:
            sign_kwargs = {
                'key': private_key,
                'cert': cert_pem.encode(),
                'reference_uri': reference_uri or None
            }
            
            signed_doc = signer.sign(doc, **sign_kwargs)
            _logger.info("Documento firmado correctamente.")
        except Exception as e:
            error_msg = f"""
            ❌ Error durante el proceso de firma electrónica:
            
            Detalle: {str(e)}
            
            Posibles causas:
            1. El certificado y la clave privada no coinciden
            2. El certificado ha expirado
            3. Problema con el formato del XML
            
            Soluciones:
            1. Verifique que el certificado y clave sean correctos
            2. Compruebe la vigencia del certificado
            3. Contacte al administrador si necesita ayuda
            """
            raise UserError(error_msg)

        # Registrar XML firmado completo en el log
        signed_xml_str = ET.tostring(signed_doc, encoding='unicode', method='xml')
        _logger.debug("XML firmado generado:\n%s", signed_xml_str)

        # Buscar elementos de la firma con manejo de errores
        try:
            signature_elem = signed_doc.xpath('//*[local-name()="Signature"]')
            if not signature_elem:
                raise UserError("""
                ❌ No se encontró la firma en el documento generado.
                
                El proceso de firma se completó pero no se pudo localizar la firma en el XML resultante.
                Esto podría indicar un problema con la estructura del XML.
                """)
                
            signature_elem = signature_elem[0]
            
            # Extraer componentes de la firma
            signed_info_elem = signature_elem.xpath('./*[local-name()="SignedInfo"]')[0]
            signature_value_elem = signature_elem.xpath('./*[local-name()="SignatureValue"]')[0]
            x509_elem = signature_elem.xpath('.//*[local-name()="X509Certificate"]')[0]
            reference_elem = signature_elem.xpath('.//*[local-name()="Reference"]')[0]
            digest_elem = signature_elem.xpath('.//*[local-name()="DigestValue"]')[0]

            # Extraer valores
            signature_value = signature_value_elem.text.strip()
            x509_text = x509_elem.text.strip()
            x509_clean = "".join(x509_text.splitlines())
            digest_value = digest_elem.text.strip()
            signed_info_xml = ET.tostring(signed_info_elem, encoding='unicode')
            reference_uri_value = reference_elem.attrib.get('URI', '')

        except (IndexError, AttributeError) as e:
            error_msg = f"""
            ❌ Estructura de firma incompleta:
            
            No se pudo encontrar un componente esencial de la firma digital.
            
            Componente faltante: {str(e)}
            
            Por favor:
            1. Verifique que el certificado sea válido
            2. Revise la configuración de firma electrónica
            3. Contacte al soporte técnico
            """
            raise UserError(error_msg)
        except Exception as e:
            _logger.exception("Error técnico al procesar firma")
            raise UserError("""
            ❌ Error inesperado al procesar la firma digital.
            
            Ocurrió un problema técnico al intentar leer los componentes de la firma.
            Por favor contacte al administrador del sistema.
            """)

        # Guardar datos en el modelo
        try:
            self.write({
                'verifactu_signature_value': signature_value,
                'verifactu_signature_date': fields.Datetime.now(),
                'verifactu_x509_certificate': x509_clean,
                'verifactu_digest_value': digest_value,
                'verifactu_signature_algorithm': "rsa-sha256",
                'verifactu_signed_info': signed_info_xml,
                'verifactu_reference_uri': reference_uri_value,
            })
            _logger.info("Datos de firma guardados correctamente.")
        except Exception as e:
            _logger.error("Error al guardar firma: %s", str(e))
            raise UserError("""
            ❌ Error al guardar los datos de la firma.
            
            La factura se firmó correctamente pero hubo un problema al guardar 
            los detalles de la firma en la base de datos.
            
            Por favor intente nuevamente o contacte al soporte técnico.
            """)

        _logger.info("Proceso de firma VeriFactu completado con éxito.")
        return signed_xml_str

    def generate_and_sign(self):
        for record in self:
            move = record.move_id
            company = move.company_id

            # Verificar configuración previa con mensajes claros
            if not company.verifactu_cert_pem:
                raise UserError("""
                ❌ Certificado digital no configurado.
                
                Para firmar facturas electrónicas debe configurar primero:
                1. Ir a Ajustes > Empresa
                2. Buscar la sección VeriFactu
                3. Cargar el certificado digital (.pem)
                """)
                
            if not company.verifactu_key_pem:
                raise UserError("""
                ❌ Clave privada no configurada.
                
                Para firmar facturas electrónicas debe configurar primero:
                1. Ir a Ajustes > Empresa
                2. Buscar la sección VeriFactu
                3. Cargar la clave privada (.pem)
                """)

            # Generar XML con manejo de errores
            try:
                xml_str = move._generate_verifactu_xml()
                
                if hasattr(xml_str, 'tag'):
                    xml_str = ET.tostring(xml_str, encoding='utf-8', method='xml').decode('utf-8')
                    
                if not xml_str or not xml_str.strip():
                    raise UserError("""
                    ❌ El XML generado está vacío.
                    
                    El sistema generó un documento XML sin contenido.
                    Por favor verifique:
                    1. Que la factura tiene todos los campos requeridos
                    2. Que los productos tienen códigos de impuestos correctos
                    """)
                    
            except AttributeError:
                raise UserError("""
                ❌ Método de generación XML no disponible.
                
                No se encontró la función '_generate_verifactu_xml' para generar 
                el XML de la factura.
                
                Por favor contacte al administrador del sistema.
                """)
            except Exception as e:
                raise UserError(f"""
                ❌ Error al generar el XML para la factura {move.name or 'sin nombre'}:
                
                Detalle del error: {str(e)}
                
                Por favor verifique:
                1. Que todos los campos requeridos están completos
                2. Que los impuestos están correctamente configurados
                3. Contacte al soporte si el error persiste
                """)

            # Firmar XML con referencia clara a la factura
            try:
                reference_uri = None              
                record._sign_verifactu_xml(
                    xml_str,
                    company.verifactu_cert_pem,
                    company.verifactu_key_pem,
                    company.verifactu_key_password,
                    reference_uri
                )
                
                # Mensaje de éxito
                move.message_post(body="✅ Factura firmada electrónicamente con éxito")
                
            except UserError as e:
                # Re-enviar los UserError tal cual
                raise e
            except Exception as e:
                _logger.exception("Error inesperado al firmar factura %s", move.name)
                raise UserError(f"""
                ❌ Error inesperado al firmar la factura {move.name or 'sin nombre'}:
                
                Ocurrió un problema técnico durante el proceso de firma.
                
                Por favor:
                1. Intente nuevamente
                2. Verifique que el certificado y clave sean válidos
                3. Contacte al soporte técnico si el problema persiste
                
                Detalle técnico: {str(e)}
                """)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Firma exitosa',
                'message': 'La factura se firmó electrónicamente correctamente',
                'type': 'success',
                'sticky': False,
            }
        }