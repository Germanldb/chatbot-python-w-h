import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import numpy as np
import logging
from io import BytesIO
import base64

logger = logging.getLogger(__name__)

class CLIPService:
    def __init__(self):
        logger.info("Cargando modelo CLIP...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        logger.info(f"✓ CLIP cargado en {self.device}")
    
    def generate_image_embedding(self, image_data):
        """Genera embedding visual de una imagen usando CLIP"""
        try:
            # Cargar imagen según el tipo de entrada
            if isinstance(image_data, str):
                # Si es base64, decodificar primero
                try:
                    image_bytes = base64.b64decode(image_data)
                    image = Image.open(BytesIO(image_bytes))
                except:
                    # Si falla, asumir que es una ruta de archivo
                    image = Image.open(image_data)
            elif isinstance(image_data, bytes):
                image = Image.open(BytesIO(image_data))
            elif isinstance(image_data, BytesIO):
                image = Image.open(image_data)
            else:
                # Ya es una imagen PIL
                image = image_data
            
            # Convertir a RGB si es necesario
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Procesar imagen
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            
            # Generar embedding
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
            
            # Normalizar
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            # Convertir a numpy
            embedding = image_features.cpu().numpy().flatten()
            
            logger.info(f"✓ Embedding generado: dimensión {len(embedding)}")
            return embedding
            
        except Exception as e:
            logger.error(f"Error generando embedding CLIP: {str(e)}")
            return None

# Instancia global
clip_service = CLIPService()
