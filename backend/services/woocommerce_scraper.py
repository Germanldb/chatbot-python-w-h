import logging
from typing import List, Dict, Optional
import httpx
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

class WooCommerceScraperService:
    def __init__(self, base_url: str = "https://winstonandharrystore.com"):
        self.base_url = base_url.rstrip('/')
        
    async def search_products(self, search_query: str, limit: int = 5) -> List[Dict]:
        """Busca productos scrapeando el sitio web"""
        try:
            search_url = f"{self.base_url}/?s={search_query}&post_type=product"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
                response = await client.get(search_url)
                
            if response.status_code != 200:
                logger.error(f"Error scraping: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            products = []
            
            # Buscar productos en el HTML
            product_items = soup.find_all('li', class_=re.compile('product'))[:limit]
            
            for item in product_items:
                try:
                    product = self._parse_product(item)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.error(f"Error parsing product: {str(e)}")
                    continue
            
            logger.info(f"Found {len(products)} products for '{search_query}'")
            return products
            
        except Exception as e:
            logger.error(f"Error in search_products: {str(e)}")
            return []
    
    def _parse_product(self, item) -> Optional[Dict]:
        """Extrae información del producto del HTML"""
        try:
            # Nombre
            name_elem = item.find('h2', class_='woocommerce-loop-product__title') or \
                       item.find('h3', class_='product-title') or \
                       item.find('a', href=True)
            name = name_elem.get_text(strip=True) if name_elem else "Producto"
            
            # Link
            link_elem = item.find('a', href=True)
            permalink = link_elem['href'] if link_elem else f"{self.base_url}/tienda"
            
            # Precio
            price_elem = item.find('span', class_='woocommerce-Price-amount') or \
                        item.find('span', class_='price')
            
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # Extraer números del precio
                price_match = re.search(r'[\d,\.]+', price_text.replace(',', ''))
                price = price_match.group(0) if price_match else "0"
            else:
                price = "Consultar"
            
            # Imagen
            img_elem = item.find('img')
            image_url = img_elem.get('src', '') or img_elem.get('data-src', '') if img_elem else ''
            
            # Descripción (si existe)
            desc_elem = item.find('div', class_='product-description') or \
                       item.find('p', class_='product-excerpt')
            description = desc_elem.get_text(strip=True)[:100] if desc_elem else ""
            
            # ID único (generado desde el link)
            product_id = hash(permalink) % 1000000
            
            return {
                "wc_id": product_id,
                "name": name,
                "price": price,
                "regular_price": price,
                "sale_price": None,
                "description": description,
                "short_description": description,
                "images": [{"src": image_url, "alt": name}] if image_url else [],
                "categories": [],
                "tags": [],
                "stock_status": "instock",
                "permalink": permalink,
                "sku": None
            }
            
        except Exception as e:
            logger.error(f"Error parsing product details: {str(e)}")
            return None

# Instancia del servicio
woocommerce_scraper = WooCommerceScraperService()
