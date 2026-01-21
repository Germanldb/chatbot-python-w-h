# Guía de Configuración: Meta WhatsApp Cloud API

Para que el chatbot funcione con tu cuenta oficial de Meta, sigue estos pasos:

### 1. Variables de Entorno
He creado un archivo llamado `env.txt` en la carpeta `backend/`. Debes:
1.  Renombrarlo a `.env` (quitarle el `.txt`).
2.  Llenar los valores con tu información real.

### 2. Configuración en Meta for Developers
1.  **App ID**: 1860897184510713
2.  **App Secret**: 318b99df1e6f24c17a912e055d8b184d
3.  Ve a **WhatsApp > Configuración de la API**.
4.  Copia el **Phone Number ID** (el de 15 dígitos) y pégalo en el `.env`.
5.  Crea un **Token de Acceso Permanente** (System User) y pégalo en `META_WHATSAPP_ACCESS_TOKEN`.

### 3. Configuración del Webhook
En el portal de Meta, ve a **WhatsApp > Configuración**:
*   **Callback URL**: `https://tu-dominio.com/api/meta/webhook` (o tu URL de ngrok).
*   **Verify Token**: `WinstonHarry2024`.
*   **Suscripciones**: Suscríbete al campo **`messages`**.

### 4. Pruebas
Una vez configurado y corriendo el servidor (`python server.py`), puedes enviar un mensaje a tu número de WhatsApp y el bot debería responder.
*   Si envías un texto: Responderá usando OpenAI.
*   Si envías una foto o captura: Activará la búsqueda visual avanzada.
