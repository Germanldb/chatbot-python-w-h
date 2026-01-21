import numpy as np
import logging
from typing import List, Dict
from motor.motor_asyncio import AsyncIOMotorClient
import os
from services.clip_service import clip_service

logger = logging.getLogger(__name__)

class VectorSearchService:
    def __init__(self):
        self.mongo_client = None
        self.db = None
        
    def _get_db(self):
        """Lazy initialization of MongoDB connection"""
        if self.db is None:
            mongo_url = os.environ.get('MONGO_URL')
            db_name = os.environ.get('DB_NAME')
            self.mongo_client = AsyncIOMotorClient(mongo_url)
            self.db = self.mongo_client[db_name]
        return self.db
        
    async def search_by_image(self, image_base64: str, top_k: int = 5) -> List[Dict]:
        """Busca productos por similitud visual usando CLIP"""
        try:
            # 1. Generar embedding VISUAL con CLIP
            logger.info("Generando embedding CLIP de imagen query...")
            query_embedding = clip_service.generate_image_embedding(image_base64)
            
            if query_embedding is None:
                logger.error("No se pudo generar embedding CLIP")
                return []
            
            logger.info(f"Embedding generado, dimensión: {len(query_embedding)}")
            
            # 2. Buscar productos similares en MongoDB
            logger.info("Buscando productos similares en MongoDB...")
            similar_products = await self.find_similar_products_mongo(query_embedding, top_k)
            
            logger.info(f"Encontrados {len(similar_products)} productos similares")
            return similar_products
            
        except Exception as e:
            logger.error(f"Error en búsqueda vectorial: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    async def find_similar_products_mongo(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict]:
        """Encuentra productos similares usando similitud coseno en MongoDB"""
        try:
            db = self._get_db()
            
            # Obtener todos los productos con embeddings
            cursor = db.product_embeddings.find(
                {"embedding": {"$exists": True, "$ne": []}},
                {"_id": 0}
            )
            
            products = await cursor.to_list(length=None)
            
            if not products:
                logger.warning("No hay productos indexados en MongoDB")
                return []
            
            logger.info(f"Evaluando {len(products)} productos...")
            
            similarities = []
            
            for product in products:
                try:
                    # Convertir embedding almacenado a numpy array
                    product_embedding = np.array(product['embedding'], dtype=np.float32)
                    
                    # Calcular similitud coseno
                    similarity = self.cosine_similarity(query_embedding, product_embedding)
                    
                    similarities.append({
                        'wc_id': product.get('wc_id'),
                        'name': product.get('name', 'Sin nombre'),
                        'price': product.get('price', ''),
                        'image_url': product.get('image_url', ''),
                        'categories': product.get('categories', ''),
                        'permalink': product.get('permalink', ''),
                        'similarity': float(similarity)
                    })
                    
                except Exception as e:
                    logger.debug(f"Error procesando producto {product.get('wc_id')}: {str(e)}")
                    continue
            
            # Ordenar por similitud descendente
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Retornar top K
            top_results = similarities[:top_k]
            
            for i, result in enumerate(top_results):
                logger.info(f"  #{i+1}: {result['name']} (similarity: {result['similarity']:.4f})")
            
            return top_results
            
        except Exception as e:
            logger.error(f"Error buscando productos similares: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calcula similitud coseno entre dos vectores"""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return np.dot(a, b) / (norm_a * norm_b)

vector_search_service = VectorSearchService()
