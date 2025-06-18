# VeriFactu para Odoo 16 (Community)

## 📄 Descripción

Este módulo permite cumplir con las obligaciones fiscales exigidas por la Agencia Tributaria (AEAT) mediante la integración del sistema **VeriFactu** en Odoo 16 Community.

Entre sus principales funcionalidades se encuentran:

- ✅ Validación de facturas con el XSD oficial de la AEAT (SuministroLR.xsd)
- 🔐 Firma electrónica mediante certificados .PEM
- 🔎 Generación de huella digital (hash) y cifrado SHA256
- 📤 Envío automático de facturas a la AEAT con seguimiento en tiempo real
- 📄 Generación de archivo XML para subida manual
- 📊 Visualización clara y estructurada de facturas para el cliente y la AEAT
- 📎 Encadenamiento de facturas con código QR y hash visible
- 📚 Historial de firmas electrónicas dentro de Odoo

> 🔧 **Próximamente disponible en versiones futuras de Odoo.**

---

## ⚙️ Requisitos

- Odoo 16 Community Edition  
- Certificados .PEM válidos emitidos por la AEAT (Certificado X.509 y Clave Privada)
- Archivo XSD oficial de la AEAT (ej. `SuministroLR.xsd`)

---

## 🚀 Instalación y Configuración

### 1. Clonar el repositorio

```bash
cd /ruta/a/tu/carpeta/addons
git clone https://github.com/nicomesa230/l10n_es_verifactu.git

### 2. Instalar el módulo desde el backend de Odoo

Ir a Apps

Hacer clic en Actualizar lista de aplicaciones

Buscar e instalar Verifactu

### 3. Subir el archivo XSD de la AEAT

Ir a Facturación/Contabilidad → VeriFactu

Subir el archivo SuministroLR.xsd renombrado como:
verifactu.xsd_path

Este archivo es necesario para validar las facturas con el esquema oficial de la AEAT.

### 4. Configurar el certificado digital

Ir a Ajustes → Usuarios y compañías → Compañías

Seleccionar tu empresa

Ir a la pestaña VeriFactu

Rellenar los siguientes campos:

Certificado X.509 (.PEM)
Comienza con:
-----BEGIN CERTIFICATE-----
Termina con:
-----END CERTIFICATE-----

Clave Privada (.PEM)
Comienza con:
-----BEGIN PRIVATE KEY-----
Termina con:
-----END PRIVATE KEY-----

Contraseña del certificado (si aplica)

El sistema guardará esta información y comenzará a firmar automáticamente las facturas.
Se puede consultar el historial en:
Facturación/Contabilidad → Firmas Electrónicas,
donde verás la fecha, hora, factura y tipo de cifrado usado (SHA256).

### 5. Enviar facturas a la AEAT

Una vez confirmada una factura, aparecerá el botón Enviar a AEAT.

Si los datos son correctos, se firmará digitalmente y se enviará directamente a la AEAT.

A su lado, verás un botón con la respuesta de la AEAT:
aceptada, rechazada o con errores detallados.

Además:

Se genera automáticamente un archivo XML descargable para envío manual si se desea.

Las facturas incluyen un código QR con la huella digital y encadenamiento entre facturas.

Se proporciona una vista clara y estructurada para el cliente y para la inspección fiscal.

### 🧩 Estado y compatibilidad

✔️ Compatible con Odoo 16 Community
🚧 Futuras versiones (Odoo 17 y siguientes) en desarrollo.

### 📬 Contacto y soporte

Este módulo es de código abierto y desarrollado para la comunidad.
Para soporte, colaboración o reportar errores, visita:
👉 https://github.com/nicomesa230/l10n_es_verifactu