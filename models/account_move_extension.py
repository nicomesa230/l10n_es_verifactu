from odoo import models, fields, api
from odoo.exceptions import UserError

class AccountMoveExtension(models.Model):
    _inherit = 'account.move'

    # Campos específicos para la integración con VeriFactu
    verifactu_hash = fields.Char("Hash VeriFactu", readonly=True, copy=False)
    verifactu_qr = fields.Binary("QR VeriFactu", readonly=True)
    verifactu_sent = fields.Boolean("Enviado a AEAT", default=False, readonly=True)
    verifactu_sent_date = fields.Datetime("Fecha envío AEAT", readonly=True)
    verifactu_csv = fields.Char("CSV (Código Seguro de Verificación)", readonly=True)
    verifactu_response = fields.Text("Respuesta AEAT", readonly=True)
    verifactu_state = fields.Selection([
        ('draft', 'Borrador'),
        ('sent', 'Enviado'),
        ('accepted', 'Aceptado'),
        ('partially_accepted', 'Aceptado parcialmente'),
        ('rejected', 'Rechazado'),
        ('error', 'Error')
    ], string="Estado VeriFactu", default='draft', readonly=True)
    verifactu_subsanacion = fields.Boolean("Es subsanación", default=False)
    verifactu_rechazo_previo = fields.Boolean("Rechazo previo", default=False)
    verifactu_xml = fields.Text("XML enviado", readonly=True)
    verifactu_signature_ids = fields.One2many('verifactu.signature', 'move_id', string="Firmas Electrónicas")
    verifactu_signature_id = fields.One2many(
        'verifactu.signature',
        'move_id',
        string='Firma VeriFactu',
        readonly=True
    )
    
