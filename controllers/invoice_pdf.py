from odoo.http import request
import logging
from functools import lru_cache

_logger = logging.getLogger(__name__)

class InvoicePDFHandler:
    
    # Tupla inmutable que define los nombres de los reportes que se pueden usar para imprimir una factura.
    # Se intentarán en orden hasta encontrar uno disponible.
    REPORT_NAMES = (
        'account.report_invoice_with_payments',
        'account.account_invoices',
        'account.report_invoice'
    )
    
    @lru_cache(maxsize=32)
    def _get_report_action(self, report_name):
        """
        Busca un reporte en el sistema por su nombre técnico (`report_name`) 
        y lo devuelve como recordset. Usa `lru_cache` para mejorar el rendimiento
        al evitar búsquedas repetidas.
        """
        try:
            report_ref = request.env['ir.actions.report'].sudo().search(
                [('report_name', '=', report_name)], 
                limit=1
            )
            return report_ref if report_ref else None
        except Exception as e:
            _logger.error(f"Error buscando reporte {report_name}: {str(e)}")
            return None

    def render_invoice_pdf(self, invoice):
        """
        Genera y devuelve el PDF de una factura.
        Se busca el primer reporte disponible en REPORT_NAMES.
        Si se genera correctamente, se retorna como respuesta HTTP para visualizar en el navegador.
        """
        # Validamos que el registro de la factura exista
        if not invoice.exists():
            _logger.error(f"Factura no existe: {invoice.id}")
            return request.not_found("La factura no existe")

        report_ref = None

        # Iteramos sobre los posibles reportes hasta encontrar uno disponible
        for report_name in self.REPORT_NAMES:
            report_ref = self._get_report_action(report_name)
            if report_ref:
                break

        # Si no se encuentra ningún reporte válido, se registra un error
        if not report_ref:
            _logger.error(f"No se encontró reporte para factura {invoice.id}")
            return request.not_found("No se pudo generar el reporte")

        try:
            # Renderizamos el reporte como PDF directamente a partir del nombre del reporte y el ID de la factura
            pdf_content, report_type = request.env['ir.actions.report']._render_qweb_pdf(
                report_ref.report_name, [invoice.id]
            )

            # Validamos que se haya generado contenido y que sea de tipo PDF
            if not pdf_content or report_type != 'pdf':
                raise ValueError("El reporte generado no es un PDF válido")

        except Exception as e:
            _logger.error(f"Error generando PDF para factura {invoice.id}: {str(e)}", exc_info=True)
            return request.not_found("Error generando el documento. Por favor, intente nuevamente.")

        # Construimos el nombre del archivo evitando caracteres problemáticos como '/'
        filename = f"factura_{invoice.name or invoice.id}.pdf".replace('/', '_')

        # Encabezados HTTP para servir el archivo como PDF en el navegador
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', f'inline; filename="{filename}"'),  # Se abre en el navegador
            ('Cache-Control', 'public, max-age=3600'),                  # Cache por 1 hora
            ('X-Content-Type-Options', 'nosniff'),                      # Seguridad adicional
            ('Content-Security-Policy', "default-src 'self'")          # Política de seguridad básica
        ]

        # Devolvemos la respuesta HTTP con el PDF generado
        return request.make_response(pdf_content, headers=headers)
