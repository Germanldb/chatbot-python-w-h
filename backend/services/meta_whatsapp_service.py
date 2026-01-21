import httpx
import os
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

class MetaWhatsAppService:
    def __init__(self):
        self.access_token = os.environ.get('META_WHATSAPP_ACCESS_TOKEN')
        self.phone_number_id = os.environ.get('META_WHATSAPP_PHONE_NUMBER_ID')
        self.api_version = os.environ.get('META_WHATSAPP_API_VERSION', 'v21.0')
        self.base_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}"

    async def send_message(self, to_number: str, text: str) -> Dict:
        """Envía un mensaje de texto vía Meta WhatsApp Cloud API"""
        if not self.access_token or not self.phone_number_id:
            logger.error("Meta WhatsApp config missing: ACCESS_TOKEN or PHONE_NUMBER_ID")
            return {"success": False, "error": "Configuración incompleta"}

        url = f"{self.base_url}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # El número debe estar en formato internacional sin el +
        clean_number = to_number.replace("+", "").replace(" ", "")
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_number,
            "type": "text",
            "text": {"body": text}
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                response_data = response.json()
                
                if response.status_code == 200:
                    logger.info(f"Mensaje enviado exitosamente a {to_number}")
                    return {"success": True, "data": response_data}
                else:
                    logger.error(f"Error enviando mensaje Meta: {response_data}")
                    return {"success": False, "error": response_data}
        except Exception as e:
            logger.error(f"Exception sending Meta message: {str(e)}")
            return {"success": False, "error": str(e)}

    async def send_image(self, to_number: str, image_url: str, caption: Optional[str] = None) -> Dict:
        """Envía una imagen vía Meta WhatsApp Cloud API"""
        url = f"{self.base_url}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        clean_number = to_number.replace("+", "").replace(" ", "")
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_number,
            "type": "image",
            "image": {
                "link": image_url,
                "caption": caption if caption else ""
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                return {"success": response.status_code == 200, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

meta_whatsapp_service = MetaWhatsAppService()
