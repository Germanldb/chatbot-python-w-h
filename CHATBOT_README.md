# Fashion Chatbot - Asistente de Moda para WhatsApp 👗👟

Un chatbot inteligente de moda para WhatsApp que puede reconocer productos en imágenes, buscarlos en tu tienda WooCommerce, y proporcionar consejos de moda personalizados.

## 🌟 Características Principales

- **Reconocimiento de Imágenes**: Los clientes pueden enviar fotos de productos y el bot los identifica usando OpenAI Vision
- **Búsqueda en WooCommerce**: Busca automáticamente productos similares en tu catálogo de WooCommerce
- **Tips de Moda**: Proporciona consejos personalizados sobre cómo combinar prendas
- **Conversaciones Naturales**: Responde de manera humana y conversacional usando GPT-4o
- **Panel de Administración**: Dashboard para monitorear conversaciones y métricas en tiempo real
- **Multi-canal**: Preparado para WhatsApp (actualmente) con soporte futuro para Instagram, Facebook y TikTok

## 🏗️ Arquitectura

```
┌─────────────────┐
│   WhatsApp      │ 
│   (Baileys)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│  Node.js        │◄────►│   FastAPI       │
│  Service        │      │   Backend       │
│  (Port 3001)    │      │   (Port 8000)   │
└─────────────────┘      └────────┬────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
            ┌─────────────┐ ┌──────────┐ ┌──────────────┐
            │  OpenAI     │ │WooCommerce│ │  MongoDB     │
            │  GPT-4o +   │ │    API    │ │              │
            │  Vision     │ │           │ │              │
            └─────────────┘ └──────────┘ └──────────────┘
```

## 🚀 Cómo Usar

### Paso 1: Conectar WhatsApp

1. Abre el panel de administración: https://smartshopper-60.preview.emergentagent.com
2. Ve a la sección "WhatsApp"
3. Escanea el código QR con tu aplicación de WhatsApp:
   - Abre WhatsApp en tu teléfono
   - Ve a Ajustes → Dispositivos vinculados
   - Toca "Vincular un dispositivo"
   - Escanea el código QR que aparece en pantalla

### Paso 2: Interactuar con el Bot

Una vez conectado, los clientes pueden:

#### 1. Enviar Fotos de Productos
```
Cliente: [Envía foto de unos zapatos]
Bot: ¡Encontré estos productos similares!

1. Zapatos Deportivos Nike Air - $89.99
   ✅ Disponible
   🔗 https://winstonandharrystore.com/producto/zapatos-nike

¿Te interesa alguno? ¡Puedo darte más detalles!
```

#### 2. Buscar por Texto
```
Cliente: Busco una camisa azul casual
Bot: Encontré estos productos:
1. Camisa Oxford Azul - $45.00
2. Camisa Denim Casual - $38.50
```

#### 3. Solicitar Consejos de Moda
```
Cliente: ¿Cómo puedo combinar esta camisa?
Bot: 💡 Consejos de moda:
1. Combínala con jeans oscuros para look casual
2. Con pantalón de vestir gris para ocasiones formales
```

## 🎨 Panel de Administración

### Dashboard
- Conversaciones totales y activas
- Productos más buscados
- Órdenes generadas

### Panel de Conversaciones
- Lista de todas las conversaciones
- Historial completo de mensajes
- Búsqueda por teléfono o nombre

## 🔧 Personalización

### Cambiar Personalidad del Bot

Edita `/app/backend/.env`:

```env
BOT_PERSONALITY="Eres un asistente de moda amigable..."
```

### Agregar Mercado Pago (Futuro)

El sistema está preparado para integrar links de pago de Mercado Pago.

## 🐛 Resolución de Problemas

### El código QR no aparece
- Espera unos segundos, el servicio está conectándose
- Refresca la página
- El QR se regenera automáticamente cada 60 segundos

### El bot no responde
1. Verifica que WhatsApp esté conectado (debe mostrar "Conectado")
2. Revisa el panel de conversaciones para ver si llegó el mensaje

### Los productos no se encuentran
- Verifica que tu tienda WooCommerce esté accesible
- Los productos deben estar publicados y activos

## 📝 Estructura del Proyecto

```
/app/
├── backend/                 # FastAPI Backend
│   ├── server.py           # Servidor principal
│   ├── services/           # OpenAI, WooCommerce, Chatbot
│   └── models/             # Modelos de datos
├── frontend/               # React Frontend
│   ├── src/components/    # Dashboard, Chat, WhatsApp
│   └── src/hooks/         # Hooks personalizados
└── whatsapp-service/      # Node.js WhatsApp (Baileys)
    └── index.js           # Servidor WhatsApp
```

## 🚧 Próximas Funciones

- [ ] Integración completa con Mercado Pago
- [ ] Soporte para Instagram Direct
- [ ] Soporte para Facebook Messenger
- [ ] Soporte para TikTok
- [ ] Sistema de plantillas de respuestas
- [ ] Análisis de sentimiento

---

Desarrollado con ❤️ para Winston and Harry Store
