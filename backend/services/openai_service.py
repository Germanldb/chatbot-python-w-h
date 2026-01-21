import os
import logging
from typing import Optional, List
import base64
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY')
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.bot_personality = os.environ.get('BOT_PERSONALITY', 'Eres un asistente de moda amigable.')
        
    async def analyze_product_image(self, image_base64: str) -> str:
        """Analiza una imagen de producto y devuelve términos de búsqueda detallados"""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto en calzado y marroquinería de lujo para Winston & Harry. Tu especialidad es identificar modelos específicos de zapatos, bolsos y accesorios de cuero. Debes ignorar elementos de interfaces de redes sociales (Instagram, WhatsApp) como likes, comentarios o nombres de usuario."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Analiza detenidamente esta imagen. Si es una captura de pantalla, busca el producto principal o texto relevante (como un SKU o nombre en la descripción). Responde con una cadena de términos de búsqueda optimizada para WooCommerce. Incluye: Tipo de producto + Color + Detalles distintivos. Responde ÚNICAMENTE con los términos de búsqueda, sin explicaciones."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=50
            )
            
            result = response.choices[0].message.content
            return result.strip().replace('"', '')
            
        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            return "zapato cuero"
    
    async def chat_with_context(self, phone_number: str, user_message: str, conversation_history: List[dict]) -> str:
        """Genera una respuesta conversacional con contexto"""
        try:
            messages = [{"role": "system", "content": self.bot_personality}]
            
            # Agregar historial
            for msg in conversation_history[-5:]:
                messages.append({"role": msg['role'], "content": msg['content']})
            
            # Agregar mensaje actual
            messages.append({"role": "user", "content": user_message})
            
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            return "Disculpa, tuve un problema al procesar tu mensaje. ¿Podrías repetirlo?"
    
    async def generate_fashion_tips(self, product_name: str) -> str:
        """Genera tips de moda relacionados con un producto"""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Eres un asesor de moda experto que da consejos prácticos y actuales."},
                    {"role": "user", "content": f"Dame 2-3 tips breves de moda sobre cómo combinar o usar: {product_name}. Sé conciso y práctico."}
                ]
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating fashion tips: {str(e)}")
            return ""

openai_service = OpenAIService()