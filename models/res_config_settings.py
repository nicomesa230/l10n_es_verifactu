from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    verifactu_xsd_attachment_id = fields.Many2one(
        'ir.attachment',
        string="Archivo XSD VeriFactu",
        help="Sube aquí el archivo XSD que se usará para validar los XML antes de enviarlos a la AEAT."
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        try:
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
                        if not attachment.exists():
                            _logger.warning("El archivo XSD configurado no existe en la base de datos")
                            attachment = False
                    except ValueError as e:
                        _logger.error("ID de archivo adjunto inválido: %s", str(e))
                        attachment = False

            if attachment and attachment.exists():
                if not attachment.datas:
                    _logger.warning("El archivo XSD existe pero no tiene contenido")
                res['verifactu_xsd_attachment_id'] = attachment.id

        except Exception as e:
            _logger.error("Error al obtener valores de configuración: %s", str(e))
            raise UserError("Ocurrió un error al cargar la configuración. Por favor intente nuevamente.")

        return res

    def set_values(self):
        try:
            super().set_values()
            if self.verifactu_xsd_attachment_id:
                # Validar que el archivo tenga contenido
                if not self.verifactu_xsd_attachment_id.datas:
                    raise UserError("El archivo XSD seleccionado está vacío. Por favor suba un archivo válido.")
                
                # Validar extensión del archivo
                if not self.verifactu_xsd_attachment_id.name.lower().endswith('.xsd'):
                    raise UserError("El archivo debe tener extensión .xsd")
                
                self.env['ir.config_parameter'].sudo().set_param(
                    'verifactu.xsd_attachment_id',
                    str(self.verifactu_xsd_attachment_id.id)
                )
            else:
                # Si se está eliminando la configuración
                self.env['ir.config_parameter'].sudo().set_param('verifactu.xsd_attachment_id', '')
                
        except UserError as e:
            raise e  # Re-lanzamos errores de usuario
        except Exception as e:
            _logger.error("Error al guardar configuración: %s", str(e))
            raise UserError("No se pudo guardar la configuración. Por favor verifique los datos e intente nuevamente.")

    def get_verifactu_xsd_path(self):
        try:
            xsd_attachment_id = self.env['ir.config_parameter'].sudo().get_param('verifactu.xsd_attachment_id')
            if not xsd_attachment_id:
                raise UserError(
                    "No se ha configurado un archivo XSD de VeriFactu.\n"
                    "Por favor vaya a Configuración → VeriFactu y suba el archivo XSD."
                )

            try:
                attachment = self.env['ir.attachment'].sudo().browse(int(xsd_attachment_id))
            except ValueError:
                raise UserError("El ID del archivo adjunto es inválido.")

            if not attachment.exists():
                raise UserError(
                    "El archivo XSD configurado no existe en el sistema.\n"
                    "Por favor vaya a Configuración → VeriFactu y suba nuevamente el archivo."
                )

            if not attachment.store_fname:
                raise UserError("El archivo XSD no tiene contenido. Por favor suba un archivo válido.")

            return attachment._full_path(attachment.store_fname)
            
        except Exception as e:
            _logger.error("Error al obtener ruta del XSD: %s", str(e))
            raise UserError("Ocurrió un error al acceder al archivo XSD. Por favor verifique la configuración.")

    def action_open_attachments(self):
        """Redirige a la lista de archivos adjuntos en la estructura técnica"""
        try:
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
        except Exception as e:
            _logger.error("Error al abrir adjuntos: %s", str(e))
            raise UserError("No se pudo abrir la vista de archivos adjuntos. Por favor intente nuevamente.")