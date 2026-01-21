"""
Servicio de Fingerprint (pHash) para identificación de imágenes de productos
Compara imágenes de clientes con el catálogo usando hash perceptual
"""
import imagehash
from PIL import Image
from io import BytesIO
import base64
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import os

logger = logging.getLogger(__name__)

class FingerprintService:
    def __init__(self):
        self.hash_size = 16  # Mayor tamaño = más preciso
        self.threshold = 15  # Diferencia máxima para considerar match (0 = idéntico)
        self.mongo_client = None
        self.db = None
    
    def _get_db(self):
        """Lazy initialization de MongoDB"""
        if self.db is None:
            mongo_url = os.environ.get('MONGO_URL')
            db_name = os.environ.get('DB_NAME')
            self.mongo_client = AsyncIOMotorClient(mongo_url)
            self.db = self.mongo_client[db_name]
        return self.db
    
    def generate_hash(self, image_data) -> str:
        """Genera pHash de una imagen"""
        try:
            # Manejar diferentes tipos de entrada
            if isinstance(image_data, str):
                # Base64
                image_bytes = base64.b64decode(image_data)
                image = Image.open(BytesIO(image_bytes))
            elif isinstance(image_data, bytes):
                image = Image.open(BytesIO(image_data))
            else:
                image = image_data
            
            # Convertir a RGB si es necesario
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Generar pHash
            phash = imagehash.phash(image, hash_size=self.hash_size)
            return str(phash)
            
        except Exception as e:
            logger.error(f"Error generando hash: {str(e)}")
            return None
    
    def compare_hashes(self, hash1: str, hash2: str) -> int:
        """Compara dos hashes y retorna la diferencia (0 = idénticos)"""
        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            return h1 - h2
        except Exception as e:
            logger.error(f"Error comparando hashes: {str(e)}")
            return 999
    
    async def find_matching_products(self, image_data, max_results: int = 3) -> list:
        """
        Busca productos que coincidan con la imagen usando fingerprint
        Retorna lista de productos con su diferencia de hash
        """
        try:
            # Generar hash de la imagen query
            query_hash = self.generate_hash(image_data)
            if not query_hash:
                logger.warning("No se pudo generar hash de la imagen")
                return []
            
            logger.info(f"Hash de imagen query: {query_hash}")
            
            db = self._get_db()
            
            # Obtener todos los productos con fingerprint
            cursor = db.product_embeddings.find(
                {"fingerprint": {"$exists": True, "$ne": None}},
                {"_id": 0, "wc_id": 1, "name": 1, "fingerprint": 1, "image_url": 1}
            )
            
            products = await cursor.to_list(length=None)
            
            if not products:
                logger.warning("No hay productos con fingerprint indexados")
                return []
            
            logger.info(f"Comparando con {len(products)} productos indexados...")
            
            # Comparar con cada producto
            matches = []
            for product in products:
                diff = self.compare_hashes(query_hash, product['fingerprint'])
                
                if diff <= self.threshold:
                    matches.append({
                        'wc_id': product['wc_id'],
                        'name': product['name'],
                        'difference': diff,
                        'image_url': product.get('image_url', '')
                    })
            
            # Ordenar por diferencia (menor = mejor match)
            matches.sort(key=lambda x: x['difference'])
            
            # Log resultados
            if matches:
                logger.info(f"✓ Encontrados {len(matches)} matches por fingerprint")
                for m in matches[:3]:
                    logger.info(f"  - {m['name']}: diff={m['difference']}")
            else:
                logger.info("No se encontraron matches por fingerprint")
            
            return matches[:max_results]
            
        except Exception as e:
            logger.error(f"Error en find_matching_products: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    async def index_product_fingerprint(self, wc_id: int, image_url: str) -> bool:
        """Indexa el fingerprint de un producto"""
        try:
            import requests
            
            # Descargar imagen
            response = requests.get(image_url, timeout=15)
            if response.status_code != 200:
                logger.error(f"No se pudo descargar imagen: {image_url}")
                return False
            
            # Generar hash
            phash = self.generate_hash(response.content)
            if not phash:
                return False
            
            # Guardar en MongoDB
            db = self._get_db()
            await db.product_embeddings.update_one(
                {"wc_id": wc_id},
                {"$set": {"fingerprint": phash}},
                upsert=False
            )
            
            logger.info(f"✓ Fingerprint indexado para producto {wc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error indexando fingerprint: {str(e)}")
            return False

fingerprint_service = FingerprintService()
