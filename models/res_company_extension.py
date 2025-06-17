from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    verifactu_cert_pem = fields.Text("Certificado X.509 (PEM)", help="Certificado público en formato PEM para firmar XML")
    verifactu_key_pem = fields.Text("Clave Privada (PEM)", help="Clave privada en formato PEM para firmar XML")
    verifactu_key_password = fields.Char("Contraseña de Clave", help="Contraseña de la clave privada, si la tiene")
