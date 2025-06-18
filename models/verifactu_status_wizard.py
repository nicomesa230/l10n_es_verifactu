from odoo import models, fields
import html

class VerifactuStatusWizard(models.TransientModel):
    _name = 'verifactu.status.wizard'
    _description = 'VeriFactu Status'

    status = fields.Char("Estado")
    sent_date = fields.Datetime("Fecha y hora de envío")
    full_response = fields.Text("Respuesta AEAT")

    def set_response(self, xml_response):
        """
        Decodifica entidades HTML y corrige caracteres especiales mal codificados.
        """
        if not xml_response:
            self.full_response = "No se recibió respuesta"
            return

        decoded = html.unescape(xml_response)

        replacements = {
            # Caracteres españoles mal codificados
            'Ã¡': 'á', 'Ã¡': 'á', 'Ã¡': 'á', 'Ã¡': 'á',
            'Ã©': 'é', 'Ã©': 'é', 'Ã©': 'é',
            'Ã­': 'í', 'Ã­': 'í', 'Ã­': 'í',
            'Ã³': 'ó', 'Ã³': 'ó', 'Ã³': 'ó',
            'Ãº': 'ú', 'Ãº': 'ú', 'Ãº': 'ú',
            'Ã±': 'ñ', 'Ã±': 'ñ', 'Ã±': 'ñ',
            'Ã¼': 'ü', 'Ã¼': 'ü',
            'Ã‘': 'Ñ', 'Ã‘': 'Ñ',
            
            # Caracteres especiales comunes
            'Ã€': 'À', 'Ã‚': 'Â', 'Ãƒ': 'Ã',
            'Ã„': 'Ä', 'Ã‡': 'Ç', 'Ãˆ': 'È',
            'Ã‰': 'É', 'ÃŠ': 'Ê', 'Ã‹': 'Ë',
            'ÃŒ': 'Ì', 'ÃŽ': 'Î', 'Ã‘': 'Ñ',
            'Ã’': 'Ò', 'Ã“': 'Ó', 'Ã”': 'Ô',
            'Ã•': 'Õ', 'Ã–': 'Ö', 'Ã™': 'Ù',
            'Ãš': 'Ú', 'Ã›': 'Û', 'Ãœ': 'Ü',
            
            # Símbolos varios
            'Ã‚': 'Â', 'Ã¢': 'â',
            'Ã£': 'ã', 'Ã¤': 'ä',
            'Ã¥': 'å', 'Ã¦': 'æ',
            'Ã§': 'ç', 'Ã¨': 'è',
            'Ãª': 'ê', 'Ã«': 'ë',
            'Ã¬': 'ì', 'Ã®': 'î',
            'Ã¯': 'ï', 'Ã°': 'ð',
            'Ãµ': 'õ', 'Ã¶': 'ö',
            'Ã¸': 'ø', 'Ã¹': 'ù',
            'Ã»': 'û', 'Ã½': 'ý',
            'Ã¿': 'ÿ',
            
            # Caracteres de control y espacios
            'Â ': ' ',  # Espacio extraño
            'Â\xa0': ' ',  # Espacio no rompible mal codificado
            'â€“': '–',  # Guión largo
            'â€”': '—',  # Raya
            'â€¢': '•',  # Viñeta
            'â€¦': '…',  # Puntos suspensivos
            'â‚¬': '€',  # Símbolo del euro
            'Â£': '£',  # Símbolo de la libra
            'Â©': '©',  # Copyright
            'Â®': '®',  # Registrado
            'Â°': '°',  # Grado
            'Â±': '±',  # Más-menos
            'Â²': '²',  # Superíndice 2
            'Â³': '³',  # Superíndice 3
            'Âµ': 'µ',  # Micro
            'Â·': '·',  # Punto medio
            'Â¼': '¼',  # Un cuarto
            'Â½': '½',  # Un medio
            'Â¾': '¾',  # Tres cuartos
            
            # Comillas y caracteres de puntuación
            'â€œ': '“',  # Comilla izquierda
            'â€': '”',   # Comilla derecha
            'â€˜': '‘',  # Comilla simple izquierda
            'â€™': '’',  # Comilla simple derecha/apóstrofe
            'â€š': '‚',  # Comilla baja
            'â€ž': '„',  # Comillas bajas dobles
            'â€¹': '‹',  # Comilla angular simple izquierda
            'â€º': '›',   # Comilla angular simple derecha
            
            # Caracteres matemáticos
            'Ã—': '×',  # Multiplicación
            'Ã·': '÷',  # División
            'Â¬': '¬',  # Negación
            'Âª': 'ª',  # Ordinal femenino
            'Âº': 'º',  # Ordinal masculino
            'Â¿': '¿',  # ¿
            'Â¡': '¡',  # ¡
            
            # Varios
            'Ã¨': 'è',
            'Ãª': 'ê',
            'Ã«': 'ë',
            'Ã®': 'î',
            'Ã¯': 'ï',
            'Ã´': 'ô',
            'Ã¶': 'ö',
            'Ã»': 'û',
            'Ã½': 'ý',
            'Ã¿': 'ÿ',
            
            # Caracteres residuales de BOM (Byte Order Mark)
            '\ufeff': '',
            '\ufffe': '',
            
            # Secuencias comunes de mal codificación
            'ÃÂ': '',  # Doble codificación residual
            'ÂÂ': '',
        }

        for wrong, right in replacements.items():
            decoded = decoded.replace(wrong, right)

        self.full_response = decoded
