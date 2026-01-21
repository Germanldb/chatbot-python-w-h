from woocommerce import API
import os
import logging
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

class WooCommerceService:
    def __init__(self):
        self.wcapi = API(
            url=os.environ.get('WOOCOMMERCE_URL'),
            consumer_key=os.environ.get('WOOCOMMERCE_CONSUMER_KEY'),
            consumer_secret=os.environ.get('WOOCOMMERCE_CONSUMER_SECRET'),
            version="wc/v3",
            timeout=30,
            user_agent="WinstonHarry Bot"
        )
        self.categories_cache = {}
        self.iva_rate = 0.19  # IVA Colombia 19%
    
    async def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        """Obtiene un producto específico por ID"""
        try:
            response = self.wcapi.get(f"products/{product_id}")
            if response.status_code == 200:
                product = response.json()
                formatted = self._format_products([product])
                return formatted[0] if formatted else None
            else:
                logger.warning(f"Product {product_id} not found: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting product {product_id}: {str(e)}")
            return None
    
    async def search_products(self, search_query: str, limit: int = 5) -> List[Dict]:
        """Busca productos en WooCommerce con lógica mejorada"""
        try:
            query_lower = search_query.lower().strip()
            products = []
            
            # Categorías conocidas (ignorar al buscar)
            known_categories = {
                "tallas grandes", "línea colombia", "linea colombia",
                "zapatos de cordón", "zapatos de cordon", "zapatos de hebilla",
                "mocasín", "mocasin", "botas", "tenis", "pantuflas",
                "accesorios", "maletas", "ropa",
                "zapato", "zapatos", "camisa", "camisas", "pantalón", "pantalones"
            }
            
            # Extraer palabras del query
            words = search_query.split()
            
            # Separar: categorías vs nombres específicos
            specific_words = []
            category_words = []
            
            for word in words:
                word_clean = word.strip('¿?¡!,.').lower()
                if word_clean in known_categories or any(cat in word_clean for cat in known_categories):
                    category_words.append(word)
                elif len(word) > 3 and word[0].isupper():  # Nombre propio (Kent, Lincoln, etc)
                    specific_words.append(word)
                elif len(word_clean) > 3:
                    specific_words.append(word)
            
            # Estrategia: Si hay nombre específico, buscar SOLO por él
            if specific_words:
                search_term = " ".join(specific_words)
                logger.info(f"Searching by specific term: '{search_term}'")
                
                response = self.wcapi.get("products", params={
                    "search": search_term,
                    "per_page": limit,
                    "status": "publish"
                })
                
                if response.status_code == 200:
                    products = response.json()
            
            # Si no encuentra con nombre específico, buscar por categoría
            if not products and category_words:
                for cat_word in category_words:
                    category_id = await self._find_category(cat_word.lower())
                    if category_id:
                        response = self.wcapi.get("products", params={
                            "category": category_id,
                            "per_page": limit,
                            "status": "publish"
                        })
                        if response.status_code == 200:
                            products = response.json()
                            if products:
                                break
            
            # Fallback: buscar por términos individuales si el completo falla
            if not products:
                # Limpiar y filtrar palabras cortas
                search_terms = [w.strip('¿?¡!,.') for w in search_query.split() if len(w) > 2]
                
                if len(search_terms) > 1:
                    logger.info(f"Fallback: Searching by terms intersection: {search_terms}")
                    # Buscar por la palabra más específica (generalmente la primera o la que no es categoría)
                    main_term = search_terms[0]
                    for term in search_terms:
                        if term.lower() not in known_categories:
                            main_term = term
                            break
                    
                    response = self.wcapi.get("products", params={
                        "search": main_term,
                        "per_page": 20,
                        "status": "publish"
                    })
                    
                    if response.status_code == 200:
                        potential_products = response.json()
                        # Filtrar manualmente para que contengan la mayoría de los términos (intersección fuzzy)
                        filtered = []
                        for p in potential_products:
                            product_text = (p['name'] + " " + p.get('description', '') + " " + p.get('short_description', '')).lower()
                            matches = sum(1 for term in search_terms if term.lower() in product_text)
                            if matches >= len(search_terms) - 1: # Permitir que falte un término si hay varios
                                filtered.append(p)
                        
                        products = filtered[:limit]

            # Fallback final: buscar por query completo (estándar de WC)
            if not products:
                response = self.wcapi.get("products", params={
                    "search": search_query,
                    "per_page": limit,
                    "status": "publish"
                })
                if response.status_code == 200:
                    products = response.json()
            
            # Último recurso: buscar ampliamente y filtrar
            if not products:
                response = self.wcapi.get("products", params={
                    "per_page": 50,
                    "status": "publish"
                })
                if response.status_code == 200:
                    all_products = response.json()
                    search_words = [w.lower() for w in specific_words if len(w) > 3]
                    if search_words:
                        products = [
                            p for p in all_products 
                            if any(word in p['name'].lower() for word in search_words)
                        ][:limit]
            
            logger.info(f"Search '{search_query}' found {len(products)} products")
            return self._format_products(products)
                
        except Exception as e:
            logger.error(f"Error searching products: {str(e)}")
            return []
    
    async def _find_category(self, search_term: str) -> Optional[int]:
        """Encuentra ID de categoría por nombre"""
        try:
            if not self.categories_cache:
                response = self.wcapi.get("products/categories", params={"per_page": 100})
                if response.status_code == 200:
                    for cat in response.json():
                        self.categories_cache[cat['slug'].lower()] = cat['id']
                        self.categories_cache[cat['name'].lower()] = cat['id']
            
            # Mapeo común de términos
            term_map = {
                "zapato": "zapatos",
                "zapatos": "zapatos",
                "camisa": "camisetas-hoodies",
                "camisas": "camisetas-hoodies",
                "pantalon": "pantalones",
                "pantalones": "pantalones",
                "bota": "botas",
                "botas": "botas",
                "chaqueta": "chaquetas",
                "chaquetas": "chaquetas"
            }
            
            search_term = term_map.get(search_term, search_term)
            return self.categories_cache.get(search_term)
            
        except Exception as e:
            logger.error(f"Error finding category: {str(e)}")
            return None
    
    def _format_products(self, products: List[Dict]) -> List[Dict]:
        """Formatea productos con precios correctos"""
        formatted = []
        for product in products:
            try:
                # Calcular precio con IVA
                price_str = product.get('price', '') or '0'
                try:
                    base_price = float(price_str) if price_str else 0
                except (ValueError, TypeError):
                    base_price = 0
                
                if base_price > 0:
                    price_with_iva = base_price * (1 + self.iva_rate)
                    # Formatear precio colombiano (puntos para miles, sin decimales)
                    price_formatted = f"{int(price_with_iva):,}".replace(',', '.')
                else:
                    price_formatted = "Consultar"
                
                formatted.append({
                    "wc_id": product.get("id"),
                    "name": product.get("name"),
                    "price": price_formatted,
                    "regular_price": price_formatted,
                    "sale_price": None,
                    "description": product.get("description", ""),
                    "short_description": product.get("short_description", ""),
                    "images": [{
                        "src": img.get("src"), 
                        "alt": img.get("alt")
                    } for img in product.get("images", [])],
                    "categories": product.get("categories", []),
                    "tags": product.get("tags", []),
                    "stock_status": product.get("stock_status", "instock"),
                    "permalink": product.get("permalink"),
                    "sku": product.get("sku")
                })
            except Exception as e:
                logger.error(f"Error formatting product: {str(e)}")
                continue
        
        return formatted

woocommerce_service = WooCommerceService()
