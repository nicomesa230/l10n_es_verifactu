from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied

class AuthHandler:

    def handle_auth_and_send(self, invoice, kwargs):
        """
        Maneja el proceso de autenticación del usuario usando username/password
        y, si es exitoso, ejecuta el envío de la factura a VeriFactu.
        """
        # Extraemos las credenciales del formulario enviado
        username = request.params.get('username')
        password = request.params.get('password')

        # Verificamos que ambos campos estén presentes
        if not username or not password:
            return self._render_login_form(invoice, error="Debe proporcionar usuario y contraseña")

        try:
            # Autenticamos al usuario contra la base de datos activa
            uid = request.session.authenticate(request.db, username, password)

            if uid:
                try:
                    # Ejecutamos la acción de envío con privilegios del usuario autenticado
                    invoice.with_user(uid).action_send_verifactu()

                    # Registramos un mensaje interno en el chatter de la factura
                    invoice.message_post(body="Factura enviada a la AEAT desde QR escaneado.")

                    # Mostramos el PDF generado tras el envío
                    return self.render_invoice_pdf(invoice)

                except Exception as e:
                    # Si ocurrió un error durante el envío, se muestra el formulario nuevamente con error
                    return self._render_login_form(invoice, error=f"Error al enviar la factura: {str(e)}")

            else:
                # Si las credenciales no son válidas, mostramos mensaje de error
                return self._render_login_form(invoice, error="Credenciales incorrectas")

        except AccessDenied:
            # Excepción específica de acceso denegado (por ejemplo, usuario deshabilitado)
            return self._render_login_form(invoice, error="Credenciales incorrectas")

        except Exception as e:
            # Otros errores inesperados durante autenticación
            return self._render_login_form(invoice, error=f"Error durante la autenticación: {str(e)}")

    def _render_login_form(self, invoice, error=None):
        """
        Genera y devuelve el formulario HTML para iniciar sesión.
        Si hay un mensaje de error, lo muestra en rojo.
        """
        html = """
        <html>
          <head><title>Iniciar sesión</title></head>
          <body style="font-family: sans-serif; padding: 20px;">
            <h2>Por favor, inicie sesión para enviar esta factura</h2>
        """
        # Si hay error, se muestra en rojo
        if error:
            html += f'<p style="color:red;">{error}</p>'

        # Formulario simple con método POST
        html += f"""
            <form method="POST">
              <label>Usuario:</label><br/>
              <input type="text" name="username" /><br/><br/>
              <label>Contraseña:</label><br/>
              <input type="password" name="password" /><br/><br/>
              <button type="submit">Enviar a AEAT</button>
            </form>
          </body>
        </html>
        """
        return html
