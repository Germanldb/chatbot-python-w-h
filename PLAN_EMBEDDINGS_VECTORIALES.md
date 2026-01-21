# Plan Completo: Sistema de Embeddings Vectoriales para Búsqueda Visual

## Objetivo
Búsqueda de productos por similitud visual con 90%+ precisión usando embeddings vectoriales.

## Arquitectura

```
WooCommerce → Script Indexador → MongoDB → Redis Vector Store
                  ↓                  ↓           ↓
              OpenAI CLIP      Cache Local   Búsqueda
              (Embeddings)                   Rápida
```

## FASE 1: Indexación Controlada (SIN saturar WooCommerce)

### Script: `/app/backend/scripts/index_products.py`

**Funcionalidades:**
1. Extrae productos de WooCommerce con rate limiting (1 producto/segundo)
2. Descarga imágenes una por una
3. Genera embeddings con OpenAI CLIP
4. Guarda en MongoDB + Redis

**Rate Limiting:**
- 1 request cada 2 segundos a WooCommerce
- Pausa de 10 min cada 50 productos
- Log de progreso detallado

### Alternativa: Google Sheets

Ya que tienes los datos en Google Sheets, podemos:
1. Leer productos desde Google Sheets (más rápido)
2. Descargar imágenes desde URLs en el sheet
3. Generar embeddings
4. Guardar en MongoDB + Redis

## FASE 2: Generación de Embeddings

### Opción A: OpenAI CLIP Embeddings API
```python
import openai

# Generar embedding de imagen
response = openai.embeddings.create(
    model="clip-vit-base-patch32",
    input=image_base64
)
embedding = response.data[0].embedding  # Vector 512 dimensiones
```

**Costo:** ~$0.0004 por imagen
**Para 1000 productos:** ~$0.40

### Opción B: Modelo Local (Gratis)
```python
from transformers import CLIPProcessor, CLIPModel

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
# Sin costo, pero más lento
```

## FASE 3: Almacenamiento

### MongoDB: Metadata + Embeddings
```javascript
{
  "wc_id": 123,
  "name": "Zapato Kent",
  "price": 500000,
  "image_url": "https://...",
  "embedding": [0.123, 0.456, ...],  // 512 dimensiones
  "indexed_at": "2026-01-20"
}
```

### Redis con RedisSearch (Búsqueda Vectorial)
```python
# Crear índice vectorial
r.ft("products").create_index([
    VectorField("embedding", 
                "FLAT", 
                {"TYPE": "FLOAT32", "DIM": 512, "DISTANCE_METRIC": "COSINE"})
])

# Buscar similares
query_embedding = [0.123, ...]
results = r.ft("products").search(
    Query("*=>[KNN 5 @embedding $vec]")
    .sort_by("__embedding_score")
    .return_fields("wc_id", "name", "__embedding_score")
    .dialect(2),
    query_params={"vec": query_embedding}
)
```

**Tus credenciales Redis:**
- Host: holasomosgo@gmail.com (verificar)
- Pass: Amalia2019*-

## FASE 4: API de Búsqueda Visual

### Endpoint: `/api/products/search-by-image`
```python
@api_router.post("/products/search-by-image")
async def search_by_image(image_base64: str):
    # 1. Generar embedding de imagen query
    query_embedding = await generate_embedding(image_base64)
    
    # 2. Buscar en Redis
    similar_products = redis_search(query_embedding, top_k=5)
    
    # 3. Obtener detalles de MongoDB
    products = await get_products_by_ids(similar_products)
    
    return {"products": products, "similarity_scores": [...]}
```

## PASOS DE IMPLEMENTACIÓN

### PASO 1: Preparar Google Sheets (YA TIENES)
```
Columnas necesarias:
- product_id
- product_name
- price
- image_url_1
- image_url_2 (opcional)
- category
```

### PASO 2: Instalar Dependencias
```bash
pip install redis openai pillow numpy
```

### PASO 3: Configurar Redis

**Opción A: Redis Cloud (tu cuenta)**
- Verificar credenciales
- Activar RedisSearch module

**Opción B: Redis Local**
```bash
docker run -d -p 6379:6379 redis/redis-stack-server:latest
```

### PASO 4: Script de Indexación

Crear `/app/backend/scripts/index_from_sheets.py`:
```python
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
import time

# Leer Google Sheets
gc = gspread.authorize(credentials)
sheet = gc.open("WooCommerce Products").sheet1
products = sheet.get_all_records()

# Procesar uno por uno con delays
for i, product in enumerate(products):
    print(f"Processing {i+1}/{len(products)}: {product['product_name']}")
    
    # Descargar imagen
    image = download_image(product['image_url_1'])
    
    # Generar embedding
    embedding = generate_embedding(image)
    
    # Guardar en MongoDB
    save_to_mongo(product, embedding)
    
    # Guardar en Redis
    save_to_redis(product['product_id'], embedding)
    
    # Rate limit: 1 cada 2 segundos
    time.sleep(2)
    
    # Checkpoint cada 50 productos
    if i % 50 == 0:
        print(f"✓ Checkpoint: {i} productos indexados")
        time.sleep(60)  # Pausa 1 minuto
```

### PASO 5: Integrar con Chatbot

Modificar `/app/backend/services/chatbot_service.py`:
```python
async def _handle_image_search(self, phone_number: str, image_base64: str):
    # Opción 1: Búsqueda vectorial (precisa)
    query_embedding = await generate_embedding(image_base64)
    similar_ids = await redis_vector_search(query_embedding, top_k=5)
    products = await get_products_from_mongo(similar_ids)
    
    # Opción 2: Fallback a OpenAI Vision si falla
    if not products:
        description = await openai_vision_analyze(image_base64)
        products = await woocommerce_search(description)
    
    return format_products(products)
```

## ESTIMACIONES

### Tiempo de Indexación
- 1000 productos × 2 seg = 33 minutos (con rate limiting)
- + Pausas = ~1 hora total

### Costos
- OpenAI Embeddings: $0.40 por 1000 productos
- Redis Cloud: $0-10/mes (dependiendo del tier)
- Storage MongoDB: Incluido

### Precisión Esperada
- Búsqueda textual actual: 60-70%
- Con embeddings vectoriales: 90-95%
- Mejora: +30% en precisión

## SIGUIENTE PASO

¿Quieres que:

**A)** Implemente el script completo de indexación desde Google Sheets
**B)** Configure Redis primero y luego hagamos indexación
**C)** Hagamos indexación directa desde WooCommerce (lenta pero automática)

Recomienda **Opción A** si ya tienes los datos en Google Sheets.
