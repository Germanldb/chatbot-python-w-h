import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import numpy as np
import logging
from io import BytesIO
import base64
import os # Added import for os

logger = logging.getLogger(__name__)

class CLIPService:
    def __init__(self):
        logger.info("Inicializando CLIPService...")
        self.model = None
        self.processor = None
        # Determine device, but don't load model yet
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = "openai/clip-vit-base-patch32"
        
        # En entornos con poca RAM (como Render Free), no cargamos el modelo al inicio
        # El modelo se cargará bajo demanda si LOW_RAM_MODE no es 'true' o 'all'
        if os.environ.get('LOW_RAM_MODE', 'true').lower() == 'false':
            self._load_model()
        logger.info(f"CLIPService inicializado. Device: {self.device}. LOW_RAM_MODE: {os.environ.get('LOW_RAM_MODE', 'true')}")

    def _load_model(self):
        """Carga el modelo solo si es necesario y aún no está cargado."""
        if self.model is None:
            try:
                logger.info(f"Cargando modelo CLIP: {self.model_name} en {self.device}...")
                self.model = CLIPModel.from_pretrained(self.model_name).to(self.device)
                self.processor = CLIPProcessor.from_pretrained(self.model_name)
                logger.info("Modelo CLIP cargado exitosamente.")
            except Exception as e:
                logger.error(f"Error cargando CLIP: {e}")
                self.model = None # Ensure model is None if loading fails
                self.processor = None
    
    def generate_image_embedding(self, image_data):
        """Genera embedding visual de una imagen usando CLIP"""
        # Check LOW_RAM_MODE for total deactivation
        if os.environ.get('LOW_RAM_MODE', 'true').lower() == 'all':
            logger.warning("CLIP embedding deshabilitado por LOW_RAM_MODE='all'.")
            return None

        self._load_model() # Attempt to load model if not already loaded
        if not self.model:
            logger.error("No se pudo cargar el modelo CLIP. No se puede generar el embedding.")
            return None

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
