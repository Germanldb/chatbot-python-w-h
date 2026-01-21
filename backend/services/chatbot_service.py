import logging
from typing import Dict, Optional, List
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import os
from services.openai_service import openai_service
from services.woocommerce_service import woocommerce_service
from services.vector_search_service import vector_search_service
from services.fingerprint_service import fingerprint_service
import re

logger = logging.getLogger(__name__)

class ChatbotService:
    def __init__(self, db):
        self.db = db
        self.conversations_collection = db.conversations
        self.products_collection = db.products
        self.bot_name = os.environ.get('BOT_NAME', 'Juan Andrés')
        
    async def process_message(self, phone_number: str, message_text: str, image_base64: Optional[str] = None) -> Dict:
        """Procesa un mensaje entrante y genera una respuesta"""
        try:
            # Obtener o crear conversación
            conversation = await self._get_or_create_conversation(phone_number)
            
            # Guardar mensaje del usuario
            await self._save_message(phone_number, "user", message_text, image_base64)
            
            # Procesar según tipo de mensaje
            if image_base64:
                # Procesar búsqueda por imagen
                response = await self._handle_image_search(phone_number, image_base64, conversation)
            else:
                # Procesar consulta de texto
                response = await self._handle_text_query(phone_number, message_text, conversation)
            
            # Guardar respuesta del bot
            await self._save_message(phone_number, "assistant", response)
            
            # Actualizar timestamp
            await self.conversations_collection.update_one(
                {"phone_number": phone_number},
                {"$set": {"updated_at": datetime.utcnow()}}
            )
            
            return {"success": True, "reply": response}
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                "success": False,
                "reply": "Disculpa, tuve un problema técnico. Por favor intenta nuevamente."
            }
    
    async def _handle_registration(self, phone_number: str, message_text: str, conversation: Dict) -> str:
        """Maneja el registro del cliente"""
        has_name = conversation.get("customer_name")
        has_email = conversation.get("customer_email")
        
        if not has_name and not has_email:
            # Primer contacto - solicitar nombre y correo
            return f"Hola, soy {self.bot_name} de Winston & Harry. ¿Me puedes compartir tu nombre y correo para ayudarte mejor?"
        
        # Intentar extraer nombre y correo del mensaje
        email = self._extract_email(message_text)
        name = self._extract_name(message_text, email)
        
        if not has_name and name:
            await self.conversations_collection.update_one(
                {"phone_number": phone_number},
                {"$set": {"customer_name": name}}
            )
            if not email:
                return f"Perfecto, {name}. Ahora necesito tu correo electrónico."
        
        if not has_email and email:
            await self.conversations_collection.update_one(
                {"phone_number": phone_number},
                {"$set": {"customer_email": email}}
            )
            if has_name or name:
                return f"Gracias. Ya estás registrado. ¿En qué puedo ayudarte hoy?"
        
        # Si aún falta información
        if not has_email:
            return "Necesito tu correo electrónico para continuar."
        if not has_name:
            return "Por favor, comparte tu nombre completo."
            
        return "Ya estás registrado. ¿En qué puedo ayudarte?"
    
    async def _handle_image_search(self, phone_number: str, image_base64: str, conversation: Dict) -> str:
        """Busca productos por imagen usando fingerprint, CLIP o Vision"""
        try:
            logger.info("Iniciando búsqueda por imagen...")
            
            # PASO 1: Fingerprint - Para imágenes de publicaciones de la marca
            fingerprint_matches = await fingerprint_service.find_matching_products(image_base64, max_results=3)
            
            if fingerprint_matches and fingerprint_matches[0]['difference'] <= 10:
                logger.info(f"✓ Match por fingerprint! Diff: {fingerprint_matches[0]['difference']}")
                
                # Obtener datos completos de WooCommerce
                formatted_products = []
                for match in fingerprint_matches:
                    if match['difference'] <= 15:  # Solo matches buenos
                        wc_product = await woocommerce_service.get_product_by_id(match['wc_id'])
                        if wc_product:
                            formatted_products.append({
                                'wc_id': match['wc_id'],
                                'name': wc_product.get('name', match['name']),
                                'price': wc_product.get('price', 'Consultar'),
                                'permalink': wc_product.get('permalink', ''),
                                'stock_status': wc_product.get('stock_status', 'instock'),
                                'short_description': ''
                            })
                
                if formatted_products:
                    await self.conversations_collection.update_one(
                        {"phone_number": phone_number},
                        {"$set": {"last_products_found": formatted_products}}
                    )
                    
                    for product in formatted_products:
                        await self._increment_product_search(product["wc_id"])
                    
                    is_exact = len(formatted_products) == 1 and fingerprint_matches[0]['difference'] <= 5
                    return self._format_products_response(formatted_products, is_exact_match=is_exact)
            
            # PASO 2: CLIP - Búsqueda vectorial
            products = await vector_search_service.search_by_image(image_base64, top_k=5)
            top_similarity = products[0].get('similarity', 0) if products else 0
            
            # Si similitud es extremadamente alta (>0.95), confiar plenamente en CLIP
            if products and top_similarity > 0.95:
                logger.info(f"CLIP: Match casi exacto {top_similarity:.4f}")
                products = [products[0]]
                formatted_products = await self._enrich_products_with_wc_data(products)
                
                await self.conversations_collection.update_one(
                    {"phone_number": phone_number},
                    {"$set": {"last_products_found": formatted_products}}
                )
                
                for product in formatted_products:
                    await self._increment_product_search(product["wc_id"])
                
                return self._format_products_response(formatted_products, is_exact_match=True)
            
            # PASO 3: Vision - Para capturas de pantalla o fotos no exactas
            logger.info(f"Buscando por Vision (CLIP top: {top_similarity:.4f})...")
            description = await openai_service.analyze_product_image(image_base64)
            logger.info(f"Vision analysis: {description}")
            
            # Buscar en WooCommerce por la descripción de Vision
            vision_products = await woocommerce_service.search_products(description, limit=5)
            
            if vision_products:
                logger.info(f"Vision encontró {len(vision_products)} productos")
                
                # Si CLIP también tenía algo bueno, podemos priorizar o combinar
                # Pero Vision suele ser más preciso para identificar el "qué" en screenshots
                await self.conversations_collection.update_one(
                    {"phone_number": phone_number},
                    {"$set": {"last_products_found": vision_products}}
                )
                
                for product in vision_products:
                    await self._increment_product_search(product["wc_id"])
                
                return self._format_products_response(vision_products)
            
            # Fallback: usar resultados de CLIP si Vision no encontró nada en la tienda
            if products and top_similarity > 0.75:
                logger.info("Vision no tuvo matches en WC, usando resultados destacados de CLIP")
                products = [p for p in products if p.get('similarity', 0) > 0.75][:3]
                formatted_products = await self._enrich_products_with_wc_data(products)
                
                if formatted_products:
                    await self.conversations_collection.update_one(
                        {"phone_number": phone_number},
                        {"$set": {"last_products_found": formatted_products}}
                    )
                    return self._format_products_response(formatted_products)
            
            return "No logré identificar el producto exacto en nuestra tienda. ¿Podrías decirme el nombre del modelo o enviarme una foto más clara?"
            
            return "No encontré productos similares en nuestro catálogo. ¿Podrías describirme qué estás buscando?"
            
        except Exception as e:
            logger.error(f"Error in image search: {str(e)}")
            return "No pude procesar la imagen. Por favor, envíala nuevamente o descríbeme qué producto buscas."
    
    async def _handle_text_query(self, phone_number: str, message_text: str, conversation: Dict) -> str:
        """Procesa consultas de texto"""
        text_lower = message_text.lower()
        
        # PRIMERO: Detectar saludos
        if self._is_greeting(text_lower):
            return "Hola. ¿En qué puedo ayudarte hoy?"
        
        # SEGUNDO: Detectar refinamiento de búsqueda anterior
        last_products = conversation.get("last_products_found", [])
        if last_products and self._is_refining_search(text_lower):
            refined_products = self._refine_previous_results(message_text, last_products)
            if refined_products:
                # Actualizar productos encontrados
                await self.conversations_collection.update_one(
                    {"phone_number": phone_number},
                    {"$set": {"last_products_found": refined_products}}
                )
                
                # Incrementar contador
                for product in refined_products:
                    await self._increment_product_search(product["wc_id"])
                
                return self._format_products_response(refined_products)
        
        # TERCERO: Detectar consulta sobre producto específico
        if last_products and self._is_asking_details(text_lower):
            return await self._handle_product_details(message_text, last_products, phone_number)
        
        # CUARTO: Detectar otras intenciones específicas
        if "tienda" in text_lower or "ubicación" in text_lower or "dirección" in text_lower:
            return f"Puedes ver nuestras ubicaciones y horarios aquí: {os.environ.get('TIENDAS_URL')}"
        
        if "talla" in text_lower and "guía" in text_lower:
            return f"Consulta nuestra guía de tallas: {os.environ.get('GUIA_TALLAS_URL')}"
        
        if "pregunta" in text_lower or "envío" in text_lower or "devolución" in text_lower or "cambio" in text_lower:
            return f"Revisa nuestras preguntas frecuentes: {os.environ.get('FAQ_URL')}"
        
        if "pedido" in text_lower or "orden" in text_lower:
            return "Para revisar tu pedido necesito el número de orden. ¿Podrías compartirlo?"
        
        # QUINTO: Intentar buscar productos
        search_terms = self._clean_search_terms(message_text)
        
        if search_terms and len(search_terms) > 2:
            logger.info(f"Searching WooCommerce for: {search_terms}")
            # Pasar el texto original (sin limpiar) para preservar mayúsculas
            products = await woocommerce_service.search_products(message_text, limit=5)
            
            if products:
                # Guardar productos
                await self.conversations_collection.update_one(
                    {"phone_number": phone_number},
                    {"$set": {"last_products_found": products}}
                )
                
                # Incrementar contador
                for product in products:
                    await self._increment_product_search(product["wc_id"])
                
                return self._format_products_response(products)
        
        # Si no encuentra nada, mensaje por defecto
        return "No encontré información con los datos que me diste. ¿Podrías verificar el nombre del producto o ser más específico?"
    
    def _format_products_response(self, products: List[Dict], is_exact_match: bool = False) -> str:
        """Formatea la respuesta con productos"""
        if not products:
            return "No encontré productos disponibles."
        
        # Si es coincidencia exacta (1 producto)
        if is_exact_match and len(products) == 1:
            product = products[0]
            name = product.get('name', 'Sin nombre')
            price = product.get('sale_price') or product.get('price') or 'Consultar precio'
            permalink = product.get('permalink', '')
            stock_status = product.get('stock_status', 'instock')
            stock_text = "Disponible" if stock_status == 'instock' else "Consultar disponibilidad"
            
            response = f"¡Encontré el producto!\n\n"
            response += f"*{name}*\n"
            response += f"Precio: ${price}\n"
            response += f"{stock_text}\n"
            response += f"{permalink}\n\n"
            response += "¿Te gustaría más información o deseas comprarlo?"
            return response
        
        response = "Estos son los productos disponibles:\n\n"
        
        for i, product in enumerate(products, 1):
            name = product.get('name', 'Sin nombre')
            price = product.get('sale_price') or product.get('price') or 'Consultar precio'
            permalink = product.get('permalink', '')
            
            # Descripción corta (máximo 80 caracteres)
            desc = product.get('short_description', '') or product.get('description', '')
            if desc:
                # Limpiar HTML
                desc = re.sub('<[^<]+?>', '', desc)
                desc = desc.strip()[:80]
                if len(desc) >= 80:
                    desc += "..."
            else:
                desc = "Producto de calidad premium"
            
            stock_status = product.get('stock_status', 'instock')
            stock_text = "Disponible" if stock_status == 'instock' else "Consultar disponibilidad"
            
            response += f"{i}. {name}\n"
            response += f"Precio: ${price}\n"
            response += f"{desc}\n"
            response += f"{stock_text}\n"
            response += f"{permalink}\n\n"
        
        response += "¿Te interesa alguno?"
        
        # Limitar respuesta a máximo 1600 caracteres (límite de WhatsApp)
        if len(response) > 1600:
            response = response[:1550] + "\n\nConsulta más productos en nuestra tienda."
        
        return response
    
    def _format_watermark_response(self, products: List[Dict]) -> str:
        """Formatea respuesta para productos identificados por watermark"""
        if len(products) == 1:
            p = products[0]
            return f"¡Encontré el producto!\n\n*{p['name']}*\nPrecio: ${p['price']}\n{p['permalink']}\n\n¿Te gustaría más información?"
        
        response = "¡Identifiqué estos productos en la imagen!\n\n"
        for i, p in enumerate(products, 1):
            response += f"{i}. *{p['name']}*\n"
            response += f"   Precio: ${p['price']}\n"
            response += f"   {p['permalink']}\n\n"
        
        response += "¿Te interesa alguno?"
        return response
    
    def _should_search_products(self, text: str) -> bool:
        """Determina si debe buscar productos"""
        keywords = [
            "zapato", "camisa", "pantalón", "vestido", "blusa", "chaqueta",
            "tenis", "sandalia", "bota", "zapatilla", "jean", "short",
            "precio", "costo", "cuánto", "cuanto", "busco", "quiero",
            "kent", "sheffield", "oxford", "derby", "loafer", "mocasín",
            "modelo", "disponible", "stock", "talla", "color"
        ]
        return any(keyword in text for keyword in keywords)
    
    def _clean_search_terms(self, text: str) -> str:
        """Limpia términos de búsqueda"""
        # Remover signos de puntuación
        text = re.sub(r'[¿?¡!,.]', '', text)
        
        # Remover palabras comunes
        stop_words = {
            "el", "la", "los", "las", "un", "una", "unos", "unas",
            "que", "tiene", "tienen", "tienes", "hay", "de", "del",
            "precio", "costo", "cuánto", "cuanto", "cuesta", "me",
            "puedes", "puedo", "quiero", "busco", "necesito", "vender",
            "y", "o", "a", "en", "con", "para", "por", "qué", "cual"
        }
        
        words = text.lower().split()
        search_terms = [word for word in words if word not in stop_words and len(word) > 2]
        
        result = " ".join(search_terms)
        logger.info(f"Cleaned search terms: '{text}' -> '{result}'")
        return result
    
    def _is_greeting(self, text: str) -> bool:
        """Detecta saludos"""
        greetings = ["hola", "buenos días", "buenas tardes", "buenas noches", "hey", "hello"]
        return any(greeting in text for greeting in greetings) and len(text.split()) <= 3
    
    def _is_refining_search(self, text: str) -> bool:
        """Detecta si está refinando búsqueda anterior"""
        refining_keywords = [
            "si", "sí", "ese", "esa", "esos", "esas", "el", "la", "los", "las",
            "zapato", "zapatos", "camisa", "camisas", "maleta", "maletas",
            "opción", "opcion", "número", "numero"
        ]
        return any(keyword in text for keyword in refining_keywords)
    
    def _is_asking_details(self, text: str) -> bool:
        """Detecta si pregunta detalles de un producto"""
        detail_keywords = [
            "color", "colores", "talla", "tallas", "disponible", "stock",
            "me interesa", "quiero", "cuál", "cual", "este", "esta"
        ]
        return any(keyword in text for keyword in detail_keywords)
    
    def _refine_previous_results(self, query: str, previous_products: List[Dict]) -> List[Dict]:
        """Refina resultados anteriores según nueva query"""
        query_lower = query.lower()
        
        # Extraer categorías específicas
        category_filters = {
            "zapato": ["zapato", "bota", "mocasín", "tenis"],
            "camisa": ["camisa"],
            "maleta": ["maleta"]
        }
        
        for category, keywords in category_filters.items():
            if category in query_lower:
                # Filtrar productos por categoría
                filtered = [
                    p for p in previous_products
                    if any(kw in p['name'].lower() for kw in keywords)
                ]
                if filtered:
                    logger.info(f"Refined to {len(filtered)} products in category '{category}'")
                    return filtered
        
        # Si menciona palabras específicas del nombre
        query_words = [w for w in query_lower.split() if len(w) > 3]
        if query_words:
            filtered = [
                p for p in previous_products
                if any(word in p['name'].lower() for word in query_words)
            ]
            if filtered:
                logger.info(f"Refined to {len(filtered)} products by keywords")
                return filtered
        
        return []
    
    async def _handle_product_details(self, query: str, last_products: List[Dict], phone_number: str) -> str:
        """Maneja consultas sobre detalles de productos específicos"""
        query_lower = query.lower()
        
        # Intentar identificar el producto de interés
        matched_product = None
        
        # Buscar por palabras clave en el nombre
        for product in last_products:
            product_name_lower = product['name'].lower()
            query_words = [w for w in query_lower.split() if len(w) > 3]
            
            if any(word in product_name_lower for word in query_words):
                matched_product = product
                break
        
        if not matched_product and last_products:
            # Si no encuentra, usar el primero de la lista
            matched_product = last_products[0]
        
        if matched_product:
            # Formatear respuesta con detalles
            response = f"Sobre el producto *{matched_product['name']}*:\n\n"
            response += f"Precio: ${matched_product['price']}\n"
            response += f"Link: {matched_product['permalink']}\n\n"
            
            # Nota sobre colores/tallas
            if "color" in query_lower or "talla" in query_lower:
                response += "Para consultar colores y tallas disponibles, por favor visita el link del producto o contáctanos directamente.\n\n"
            
            response += "¿Deseas información sobre otro producto?"
            return response
        
        return "No encontré el producto específico. ¿Podrías ser más específico?"
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extrae email del mensaje"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        return match.group(0) if match else None
    
    def _extract_name(self, text: str, email: Optional[str] = None) -> Optional[str]:
        """Extrae nombre del mensaje"""
        # Remover email si existe
        if email:
            text = text.replace(email, "")
        
        # Buscar palabras que empiecen con mayúscula (probable nombre)
        words = text.split()
        name_words = [w for w in words if w and w[0].isupper() and len(w) > 2]
        
        if len(name_words) >= 2:
            return " ".join(name_words[:3])  # Máximo 3 palabras
        
        return None
    
    async def _get_or_create_conversation(self, phone_number: str) -> Dict:
        """Obtiene o crea una conversación"""
        conversation = await self.conversations_collection.find_one({"phone_number": phone_number})
        
        if not conversation:
            conversation = {
                "phone_number": phone_number,
                "messages": [],
                "status": "active",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            await self.conversations_collection.insert_one(conversation)
        
        return conversation
    
    async def _save_message(self, phone_number: str, role: str, content: str, image_url: Optional[str] = None):
        """Guarda un mensaje"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow()
        }
        if image_url:
            message["image_url"] = image_url
        
        await self.conversations_collection.update_one(
            {"phone_number": phone_number},
            {"$push": {"messages": message}}
        )
    
    async def _increment_product_search(self, product_id: int):
        """Incrementa contador de búsquedas"""
        await self.products_collection.update_one(
            {"wc_id": product_id},
            {"$inc": {"search_count": 1}},
            upsert=True
        )
    
    async def _enrich_products_with_wc_data(self, products: List[Dict]) -> List[Dict]:
        """Enriquece productos de búsqueda vectorial con datos actuales de WooCommerce"""
        enriched = []
        
        for p in products:
            try:
                # Intentar obtener datos de WooCommerce por ID
                wc_product = await woocommerce_service.get_product_by_id(p['wc_id'])
                
                if wc_product:
                    enriched.append({
                        'wc_id': p['wc_id'],
                        'name': wc_product.get('name', p['name']),
                        'price': wc_product.get('price', 'Consultar'),
                        'permalink': wc_product.get('permalink', p.get('permalink', '')),
                        'stock_status': wc_product.get('stock_status', 'instock'),
                        'short_description': f"Similitud: {int(p.get('similarity', 0) * 100)}%"
                    })
                else:
                    # Fallback a datos de MongoDB
                    enriched.append({
                        'wc_id': p['wc_id'],
                        'name': p['name'],
                        'price': 'Consultar',
                        'permalink': p.get('permalink', p.get('image_url', '')),
                        'stock_status': 'instock',
                        'short_description': f"Similitud: {int(p.get('similarity', 0) * 100)}%"
                    })
            except Exception as e:
                logger.error(f"Error enriching product {p.get('wc_id')}: {str(e)}")
                enriched.append({
                    'wc_id': p['wc_id'],
                    'name': p['name'],
                    'price': 'Consultar',
                    'permalink': p.get('permalink', ''),
                    'stock_status': 'instock',
                    'short_description': f"Similitud: {int(p.get('similarity', 0) * 100)}%"
                })
        
        return enriched

chatbot_service = None
