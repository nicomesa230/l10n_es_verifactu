from odoo import models, fields, api
from odoo.http import request
from odoo import http
import base64

class AccountMove(models.Model):
    _inherit = 'account.move'

    #Generamos XML para verifactu
    def action_download_verifactu_xml(self):
        self.ensure_one()
        xml_content = self._generate_verifactu_xml()
        filename = f"factura_{self.name.replace('/', '_')}.xml"
        action = {
            'type': 'ir.actions.act_url',
            'url': f"/verifactu/download_xml/{self.id}",
            'target': 'new',
        }
        return action
