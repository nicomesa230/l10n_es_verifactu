from odoo import models, fields, api
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    #Buscamos el archivo para poder guardarlo en el sistema
    verifactu_xsd_attachment_id = fields.Many2one(
        'ir.attachment',
        string="Archivo XSD VeriFactu",
        help="Sube aquí el archivo XSD que se usará para validar los XML antes de enviarlos a la AEAT."
    )

    @api.model
    def get_values(self):
        res = super().get_values()

        # Busca automáticamente el archivo XSD por nombre y modelo
        attachment = self.env['ir.attachment'].sudo().search([
            ('name', '=', 'verifactu_schema.xsd'),
            ('res_model', '=', 'res.config.settings')
        ], limit=1)

        if not attachment:
            param = self.env['ir.config_parameter'].sudo().get_param('verifactu.xsd_attachment_id')
            if param:
                try:
                    attachment = self.env['ir.attachment'].sudo().browse(int(param))
                except ValueError:
                    pass

        if attachment and attachment.exists():
            res['verifactu_xsd_attachment_id'] = attachment.id

        return res


    #Actualiza los campos relacionales
    def set_values(self):
        super().set_values()
        if self.verifactu_xsd_attachment_id:
            self.env['ir.config_parameter'].sudo().set_param(
                'verifactu.xsd_attachment_id',
                str(self.verifactu_xsd_attachment_id.id)
            )

    #Busca en odoo el campo relacionar y los devuelve al frontend
    def get_verifactu_xsd_path(self):
        xsd_attachment_id = self.env['ir.config_parameter'].sudo().get_param('verifactu.xsd_attachment_id')
        if not xsd_attachment_id:
            raise UserError("No se ha configurado un archivo XSD de VeriFactu.")

        attachment = self.env['ir.attachment'].sudo().browse(int(xsd_attachment_id))
        if not attachment.exists():
            raise UserError("El archivo XSD configurado no existe.")

        return attachment._full_path(attachment.store_fname)

    #Redirige al accionar la función a la vista para subir el .xsd para hacer el validador de verifactu
    def action_open_attachments(self):
        """Redirige a la lista de archivos adjuntos en la estructura técnica"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Archivos adjuntos',
            'res_model': 'ir.attachment',
            'view_mode': 'tree,form',
            'views': [(False, 'tree'), (False, 'form')],
            'target': 'current',
            'domain': [('res_model', '=', 'res.config.settings')],
            'context': {
                'default_res_model': 'res.config.settings',
                'default_res_id': self.id,
            },
            'search_view_id': [self.env.ref('base.view_attachment_search').id],
        }