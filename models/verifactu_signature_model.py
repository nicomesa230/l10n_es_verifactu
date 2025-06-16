from odoo import models, fields

class VeriFactuSignature(models.Model):
    _name = 'verifactu.signature'
    _description = 'Firma Electrónica VeriFactu'
    _order = 'create_date desc'

    move_id = fields.Many2one('account.move', string='Factura', required=True, ondelete='cascade', index=True)

    # Campos para la firma electrónica y enviar los datos en el XML 
    verifactu_signature_value = fields.Text("Firma XML", readonly=True)
    verifactu_signature_date = fields.Datetime("Fecha de Firma", readonly=True)
    verifactu_x509_certificate = fields.Text("Certificado X.509", readonly=True)
    verifactu_digest_value = fields.Char("Digest Value", readonly=True)
    verifactu_signature_algorithm = fields.Char("Algoritmo de Firma", readonly=True)
    verifactu_signed_info = fields.Text("SignedInfo XML", readonly=True)
    verifactu_reference_uri = fields.Char("Referencia URI", readonly=True)

    def _sign_verifactu_xml(self, xml_str, cert_pem, key_pem, key_pass=None):
        # Cargar clave privada
        private_key = load_pem_private_key(key_pem.encode(), password=key_pass.encode() if key_pass else None, backend=default_backend())

        # Parsea el XML
        doc = ET.fromstring(xml_str.encode('utf-8'))

        # Firmar (firma enveloped dentro del XML)
        signer = XMLSigner(method=methods.enveloped, signature_algorithm="rsa-sha256", digest_algorithm="sha256")
        signed_doc = signer.sign(doc, key=private_key, cert=cert_pem.encode())

        # Extraer la firma generada
        signature_elem = signed_doc.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature')
        signed_info_elem = signature_elem.find('{http://www.w3.org/2000/09/xmldsig#}SignedInfo')
        signature_value_elem = signature_elem.find('{http://www.w3.org/2000/09/xmldsig#}SignatureValue')
        x509_elem = signature_elem.find('.//{http://www.w3.org/2000/09/xmldsig#}X509Certificate')
        reference_elem = signature_elem.find('.//{http://www.w3.org/2000/09/xmldsig#}Reference')
        digest_elem = signature_elem.find('.//{http://www.w3.org/2000/09/xmldsig#}DigestValue')

        # Convertir elementos a string
        signed_info_xml = ET.tostring(signed_info_elem, encoding='unicode')
        signature_value = signature_value_elem.text
        x509_cert = x509_elem.text
        digest_value = digest_elem.text
        reference_uri = reference_elem.attrib.get('URI', '')

        # Guardar los datos en el modelo
        self.verifactu_signature_value = signature_value
        self.verifactu_signature_date = fields.Datetime.now()
        self.verifactu_x509_certificate = x509_cert
        self.verifactu_digest_value = digest_value
        self.verifactu_signature_algorithm = "rsa-sha256"
        self.verifactu_signed_info = signed_info_xml
        self.verifactu_reference_uri = reference_uri

        # Retorna el XML firmado como string
        return ET.tostring(signed_doc, encoding='utf-8', method='xml').decode('utf-8')
