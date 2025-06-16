from odoo import http
from odoo.http import request, content_disposition

class VeriFactuDownloadController(http.Controller):

    #Descargamos via web el XML de nuestro verifactu
    @http.route('/verifactu/download_xml/<int:invoice_id>', type='http', auth='user')
    def download_xml(self, invoice_id, **kwargs):
        invoice = request.env['account.move'].sudo().browse(invoice_id)
        if not invoice.exists():
            return request.not_found()

        try:
            xml_data = invoice._generate_verifactu_xml()
            filename = f"factura_{invoice.name.replace('/', '_')}.xml"
            headers = [
                ('Content-Type', 'application/xml'),
                ('Content-Disposition', content_disposition(filename)),
            ]
            return request.make_response(xml_data, headers)
        except Exception as e:
            return request.make_response(
                f"<h2>Error generando XML:</h2><pre>{str(e)}</pre>",
                [('Content-Type', 'text/html')]
            )
