"""
Servicio de Watermarking Ultra-Robusto para productos
Diseñado para sobrevivir compresión agresiva de WhatsApp
"""
import cv2
import numpy as np
from PIL import Image
from io import BytesIO
import base64
import logging

logger = logging.getLogger(__name__)

class WatermarkService:
    def __init__(self):
        self.prefix = "WH"
        self.block_size = 8
        self.strength = 100  # Fuerza alta para sobrevivir compresión
        self.repetitions = 10  # Mucha redundancia
    
    def _text_to_bits(self, text: str) -> list:
        """Convierte texto a lista de bits"""
        bits = []
        for char in text:
            char_bits = format(ord(char), '08b')
            bits.extend([int(b) for b in char_bits])
        return bits
    
    def _bits_to_text(self, bits: list) -> str:
        """Convierte lista de bits a texto"""
        chars = []
        for i in range(0, len(bits), 8):
            byte = bits[i:i+8]
            if len(byte) == 8:
                char_code = int(''.join(map(str, byte)), 2)
                if 32 <= char_code <= 126:
                    chars.append(chr(char_code))
        return ''.join(chars)
    
    def _majority_vote(self, bit_lists: list) -> list:
        """Voto por mayoría para recuperar bits con errores"""
        if not bit_lists:
            return []
        
        min_len = min(len(bl) for bl in bit_lists)
        result = []
        
        for i in range(min_len):
            votes = [bl[i] for bl in bit_lists if i < len(bl)]
            result.append(1 if sum(votes) > len(votes) / 2 else 0)
        
        return result
    
    def encode_products(self, image_data: bytes, product_ids: list) -> bytes:
        """Incrusta IDs de productos con máxima robustez"""
        try:
            # Formato corto: WH24112-32298
            code = f"{self.prefix}{'-'.join(map(str, product_ids))}"
            logger.info(f"Codificando watermark robusto: {code}")
            
            img_array = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if img is None:
                return image_data
            
            # Convertir a YCrCb
            img_ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
            y_channel = img_ycrcb[:, :, 0].astype(float)
            
            bits = self._text_to_bits(code)
            bits.extend([0] * 8)  # Terminador
            
            h, w = y_channel.shape
            
            # Embeber con múltiples repeticiones en diferentes posiciones
            for rep in range(self.repetitions):
                bit_idx = 0
                # Offset diferente para cada repetición
                offset_i = (rep * 17) % self.block_size
                offset_j = (rep * 13) % self.block_size
                
                for i in range(offset_i, h - self.block_size, self.block_size * 2):
                    for j in range(offset_j, w - self.block_size, self.block_size * 2):
                        if bit_idx >= len(bits):
                            break
                        
                        block = y_channel[i:i+self.block_size, j:j+self.block_size]
                        dct_block = cv2.dct(block)
                        
                        bit = bits[bit_idx]
                        
                        # Usar múltiples coeficientes para robustez
                        positions = [(3, 3), (3, 4), (4, 3), (4, 4), (5, 5)]
                        for pi, pj in positions:
                            if bit == 1:
                                dct_block[pi, pj] = abs(dct_block[pi, pj]) + self.strength
                            else:
                                dct_block[pi, pj] = -abs(dct_block[pi, pj]) - self.strength
                        
                        y_channel[i:i+self.block_size, j:j+self.block_size] = cv2.idct(dct_block)
                        bit_idx += 1
            
            y_channel = np.clip(y_channel, 0, 255).astype(np.uint8)
            img_ycrcb[:, :, 0] = y_channel
            img_watermarked = cv2.cvtColor(img_ycrcb, cv2.COLOR_YCrCb2BGR)
            
            success, encoded_bytes = cv2.imencode('.png', img_watermarked)
            
            if success:
                logger.info(f"✓ Watermark robusto aplicado")
                return encoded_bytes.tobytes()
            
            return image_data
            
        except Exception as e:
            logger.error(f"Error en encode_products: {str(e)}")
            return image_data
    
    def decode_products(self, image_data) -> list:
        """Extrae IDs con voto por mayoría para máxima robustez"""
        try:
            if isinstance(image_data, str):
                image_data = base64.b64decode(image_data)
            
            img_array = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if img is None:
                return []
            
            img_ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
            y_channel = img_ycrcb[:, :, 0].astype(float)
            
            h, w = y_channel.shape
            all_bit_lists = []
            
            # Extraer de múltiples repeticiones
            for rep in range(self.repetitions):
                extracted_bits = []
                offset_i = (rep * 17) % self.block_size
                offset_j = (rep * 13) % self.block_size
                
                for i in range(offset_i, h - self.block_size, self.block_size * 2):
                    for j in range(offset_j, w - self.block_size, self.block_size * 2):
                        if len(extracted_bits) >= 200:
                            break
                        
                        block = y_channel[i:i+self.block_size, j:j+self.block_size]
                        dct_block = cv2.dct(block)
                        
                        # Leer de múltiples posiciones y votar
                        positions = [(3, 3), (3, 4), (4, 3), (4, 4), (5, 5)]
                        votes = [1 if dct_block[pi, pj] > 0 else 0 for pi, pj in positions]
                        bit = 1 if sum(votes) > len(votes) / 2 else 0
                        extracted_bits.append(bit)
                
                all_bit_lists.append(extracted_bits)
            
            # Voto por mayoría entre todas las repeticiones
            final_bits = self._majority_vote(all_bit_lists)
            decoded_text = self._bits_to_text(final_bits)
            
            logger.info(f"Texto extraído: {decoded_text[:30]}...")
            
            # Buscar nuestro prefijo
            if self.prefix in decoded_text:
                start_idx = decoded_text.find(self.prefix)
                code_part = decoded_text[start_idx + len(self.prefix):]
                
                ids = []
                current_num = ""
                for char in code_part:
                    if char.isdigit():
                        current_num += char
                    elif char == '-' and current_num:
                        if len(current_num) >= 4:  # IDs válidos tienen al menos 4 dígitos
                            ids.append(int(current_num))
                        current_num = ""
                    elif not char.isdigit() and current_num:
                        if len(current_num) >= 4:
                            ids.append(int(current_num))
                        break
                
                if current_num and len(current_num) >= 4:
                    ids.append(int(current_num))
                
                if ids:
                    logger.info(f"✓ IDs extraídos: {ids}")
                    return ids
            
            return []
            
        except Exception as e:
            logger.error(f"Error en decode_products: {str(e)}")
            return []
    
    def encode_image_base64(self, image_base64: str, product_ids: list) -> str:
        """Versión que trabaja con base64"""
        try:
            image_bytes = base64.b64decode(image_base64)
            encoded_bytes = self.encode_products(image_bytes, product_ids)
            return base64.b64encode(encoded_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f"Error en encode_image_base64: {str(e)}")
            return image_base64

watermark_service = WatermarkService()
