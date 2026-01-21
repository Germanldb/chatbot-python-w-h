# PRD - Chatbot Winston & Harry

## Problema Original
Chatbot con apariencia humana para tienda de zapatos y ropa (Winston & Harry) con las siguientes funcionalidades:
1. Reconocer productos a partir de fotos enviadas por WhatsApp
2. Buscar productos en la tienda WooCommerce
3. Devolver nombre y precio del producto
4. Enviar enlace de pago de Mercado Pago (si el cliente lo solicita)
5. Proporcionar consejos de moda
6. Personalidad "Juan Andrés": confiable, directo, elegante

## Arquitectura
- **Backend**: FastAPI (Python)
- **Frontend**: React (Dashboard de administración)
- **Base de datos**: MongoDB (conversaciones, embeddings)
- **Integraciones**: Twilio (WhatsApp), WooCommerce API, OpenAI GPT-4o
- **ML**: CLIP (embeddings visuales para búsqueda por imagen)

## Estado Actual

### Funcionalidades Completadas
- [x] Integración WhatsApp vía Twilio
- [x] Búsqueda de productos por texto (WooCommerce)
- [x] Búsqueda de productos por imagen (CLIP + MongoDB vectorial)
- [x] Personalidad del bot configurada
- [x] Dashboard de administración básico
- [x] Precios con IVA (19%)
- [x] 317 productos indexados con embeddings CLIP

### Funcionalidades Pendientes
- [ ] **(P1)** Enlaces de pago con Mercado Pago
- [ ] **(P1)** Contexto conversacional mejorado (refinamiento de búsqueda)
- [ ] **(P2)** Flujo de registro de clientes (nombre/correo)
- [ ] **(P2)** Consejos de moda
- [ ] **(P3)** Indexar catálogo completo (~5000 productos)
- [ ] **(P3)** Integrar Instagram, Facebook, TikTok

## Archivos Clave
- `/app/backend/services/chatbot_service.py` - Lógica principal del bot
- `/app/backend/services/vector_search_service.py` - Búsqueda vectorial (MongoDB)
- `/app/backend/services/clip_service.py` - Generación de embeddings CLIP
- `/app/backend/services/woocommerce_service.py` - API WooCommerce
- `/app/backend/server.py` - Endpoints FastAPI

## Changelog
- **2026-01-21**: Corregida búsqueda por imagen. Migrado de Redis a MongoDB para almacenamiento de vectores. La búsqueda vectorial ahora funciona correctamente con similitud coseno sobre embeddings CLIP.
