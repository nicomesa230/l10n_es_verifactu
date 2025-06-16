from odoo import http
from odoo.http import request
import logging

# Importamos las clases auxiliares para manejar PDF e inicio de sesión
from .invoice_pdf import InvoicePDFHandler
from .auth_handler import AuthHandler

_logger = logging.getLogger(__name__)

class QRScannerController(http.Controller):
    @http.route('/verifactu/scan/<string:hash_value>', auth='user', website=True, csrf=False)
    def verifactu_scan(self, hash_value, **kwargs):
        """
        Ruta pública que se activa al escanear el código QR de una factura.
        Busca la factura por su hash y realiza una de las siguientes acciones:
        - Si ya está enviada a VeriFactu, muestra el PDF.
        - Si no lo está, muestra el formulario de autenticación o lo procesa.
        """
        try:
            # Buscamos la factura asociada al hash recibido
            invoice = request.env['account.move'].sudo().search(
                [('verifactu_hash', '=', hash_value)], 
                limit=1
            )

            # Si no se encuentra ninguna factura, devolvemos un 404
            if not invoice:
                _logger.warning(f"Factura no encontrada para hash: {hash_value}")
                return request.not_found("Factura no encontrada")

            # Si la factura ya fue enviada a VeriFactu, mostramos directamente el PDF
            if invoice.verifactu_sent:
                return InvoicePDFHandler().render_invoice_pdf(invoice)

            # Si se ha enviado un formulario (método POST), procesamos la autenticación
            if request.httprequest.method == 'POST':
                return AuthHandler().handle_auth_and_send(invoice, kwargs)

            # En caso contrario, mostramos el formulario de autenticación
            return AuthHandler()._render_login_form(invoice)

        except Exception as e:
            # En caso de error grave, lo registramos y mostramos una página HTML sencilla de error
            _logger.critical(f"Error crítico en /verifactu/scan/{hash_value}: {str(e)}", exc_info=True)
            return request.make_response("""
                <!DOCTYPE html>
                <html><body>
                    <h2>Error interno</h2>
                    <p><a href="/">Volver</a></p>
                </body></html>
            """, headers=[('Content-Type', 'text/html')])
