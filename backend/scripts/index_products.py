#!/usr/bin/env python3
"""
Script de indexación de productos con embeddings vectoriales CLIP
Lee CSV de WooCommerce y genera embeddings visuales para búsqueda
"""

import pandas as pd
import redis
import requests
import base64
import time
import logging
from io import BytesIO
from PIL import Image
import numpy as np
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import os
from dotenv import load_dotenv
import sys
sys.path.append('/app/backend')
from services.clip_service import clip_service

# Configuración
load_dotenv('/app/backend/.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Conexiones
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=False)
mongo_client = AsyncIOMotorClient(os.environ.get('MONGO_URL'))
db = mongo_client[os.environ.get('DB_NAME')]

# Configuración
RATE_LIMIT_DELAY = 2  # segundos entre cada producto
CHECKPOINT_INTERVAL = 50  # guardar progreso cada N productos
CHECKPOINT_FILE = '/app/backend/indexing_progress.txt'

class ProductIndexer:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.processed_count = 0
        self.failed_count = 0
        self.start_from = self.load_checkpoint()
        
    def load_checkpoint(self):
        """Carga el progreso guardado"""
        try:
            if os.path.exists(CHECKPOINT_FILE):
                with open(CHECKPOINT_FILE, 'r') as f:
                    return int(f.read().strip())
        except:
            pass
        return 0
    
    def save_checkpoint(self, index):
        """Guarda el progreso"""
        with open(CHECKPOINT_FILE, 'w') as f:
            f.write(str(index))
    
    async def index_products(self):
        """Indexa todos los productos desde el CSV"""
        logger.info(f"Cargando CSV desde {self.csv_path}")
        df = pd.read_csv(self.csv_path)
        
        # Filtrar solo productos principales (no variaciones)
        df = df[df['Tipo'].isin(['simple', 'variable'])]
        
        total = len(df)
        logger.info(f"Total de productos a indexar: {total}")
        logger.info(f"Comenzando desde producto #{self.start_from}")
        
        for idx, row in df.iterrows():
            if idx < self.start_from:
                continue
            
            try:
                await self.process_product(row, idx, total)
                self.processed_count += 1
                
                # Checkpoint
                if self.processed_count % CHECKPOINT_INTERVAL == 0:
                    self.save_checkpoint(idx + 1)
                    logger.info(f"✓ Checkpoint: {self.processed_count} productos procesados")
                    logger.info(f"  Pausando 30 segundos...")
                    time.sleep(30)
                
                # Rate limiting
                time.sleep(RATE_LIMIT_DELAY)
                
            except Exception as e:
                logger.error(f"Error procesando producto {idx}: {str(e)}")
                self.failed_count += 1
                continue
        
        logger.info(f"\n{'='*60}")
        logger.info(f"INDEXACIÓN COMPLETADA")
        logger.info(f"  Procesados: {self.processed_count}")
        logger.info(f"  Fallidos: {self.failed_count}")
        logger.info(f"{'='*60}")
        
        # Limpiar checkpoint
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
    
    async def process_product(self, row, idx, total):
        """Procesa un producto individual"""
        product_id = int(row['ID'])
        product_name = row['Nombre']
        
        logger.info(f"[{idx+1}/{total}] Procesando: {product_name}")
        
        # Obtener imagen principal
        images = str(row['Imágenes']).split(',') if pd.notna(row['Imágenes']) else []
        if not images or images[0] == 'nan':
            logger.warning(f"  ⚠ Sin imagen, saltando...")
            return
        
        image_url = images[0].strip()
        
        # Descargar imagen
        logger.info(f"  → Descargando imagen...")
        image_data = self.download_image(image_url)
        if not image_data:
            logger.warning(f"  ⚠ No se pudo descargar imagen")
            return
        
        # Generar embedding
        logger.info(f"  → Generando embedding...")
        embedding = await self.generate_embedding(image_data)
        if embedding is None or len(embedding) == 0:
            logger.warning(f"  ⚠ No se pudo generar embedding")
            return
        
        # Preparar datos del producto
        product_data = {
            'wc_id': product_id,
            'name': product_name,
            'price': str(row.get('Precio normal', '')),
            'categories': str(row.get('Categorías', '')),
            'tags': str(row.get('Etiquetas', '')),
            'image_url': image_url,
            'permalink': f"https://winstonandharrystore.com/product/{row.get('SKU', product_id)}/",
            'embedding': embedding.tolist(),
            'indexed_at': pd.Timestamp.now().isoformat()
        }
        
        # Guardar en MongoDB
        logger.info(f"  → Guardando en MongoDB...")
        await db.product_embeddings.update_one(
            {'wc_id': product_id},
            {'$set': product_data},
            upsert=True
        )
        
        # Guardar en Redis
        logger.info(f"  → Guardando en Redis...")
        self.save_to_redis(product_id, embedding, product_data)
        
        logger.info(f"  ✓ Completado")
    
    def download_image(self, url):
        """Descarga una imagen desde URL"""
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.content
        except Exception as e:
            logger.error(f"Error descargando imagen: {str(e)}")
        return None
    
    async def generate_embedding(self, image_data):
        """Genera embedding usando CLIP"""
        try:
            # Usar CLIP service
            embedding = clip_service.generate_image_embedding(image_data)
            return embedding
            
        except Exception as e:
            logger.error(f"Error generando embedding CLIP: {str(e)}")
            return None
    
    def save_to_redis(self, product_id, embedding, metadata):
        """Guarda embedding en Redis"""
        try:
            # Convertir embedding a bytes
            embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()
            
            # Guardar en Redis con hash
            key = f"product:{product_id}"
            redis_client.hset(key, mapping={
                'embedding': embedding_bytes,
                'name': metadata['name'],
                'price': metadata['price'],
                'image_url': metadata['image_url']
            })
            
        except Exception as e:
            logger.error(f"Error guardando en Redis: {str(e)}")

async def main():
    """Función principal"""
    csv_path = '/tmp/products.csv'
    
    if not os.path.exists(csv_path):
        logger.error(f"CSV no encontrado en {csv_path}")
        return
    
    indexer = ProductIndexer(csv_path)
    await indexer.index_products()

if __name__ == '__main__':
    asyncio.run(main())
