from odoo import models, fields, api
from odoo.http import request
from odoo import http
import base64
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_download_verifactu_xml(self):
        try:
            self.ensure_one()
            if not self.name:
                raise UserError("El documento no tiene un nombre/número asignado.")
            
            # Válida el documento
            if self.move_type not in ('out_invoice', 'out_refund'):
                raise UserError("Solo se pueden generar XML para facturas de cliente y notas de crédito.")
            
            # Genera el xml y si no puede generarlo lanza una excepción
            xml_content = self._generate_verifactu_xml()
            if not xml_content:
                raise UserError("No se pudo generar el contenido XML. Verifique los datos del documento.")
                
            filename = f"factura_{self.name.replace('/', '_')}.xml"
            action = {
                'type': 'ir.actions.act_url',
                'url': f"/verifactu/download_xml/{self.id}",
                'target': 'new',
            }
            return action
            
        except UserError as e:
            
            raise e
        except Exception as e:
            # Agregamos logs si algo falla externo dentro del server
            _logger.error("Error generating Verifactu XML: %s", str(e))
            raise UserError("Ocurrió un error al preparar el XML. El archivo puede estar incompleto o incorrecto. Detalles técnicos: %s" % str(e))