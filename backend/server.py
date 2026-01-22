from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form, Request, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, List
import base64
from datetime import datetime, timedelta
import httpx

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Import services
from services.chatbot_service import ChatbotService
from services.woocommerce_service import woocommerce_service
from services.vector_search_service import vector_search_service
from services.meta_whatsapp_service import meta_whatsapp_service

chatbot_service = ChatbotService(db)

# Create the main app
app = FastAPI(title="Fashion Chatbot API")
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Models
class WhatsAppMessage(BaseModel):
    phone_number: str
    message: str
    message_id: str
    timestamp: int
    image_base64: Optional[str] = None

class MessageResponse(BaseModel):
    success: bool
    reply: str

class DashboardStats(BaseModel):
    total_conversations: int
    active_conversations: int
    total_products_searched: int
    total_orders: int
    revenue_today: float

# Routes
@api_router.get("/")
async def root():
    return {"message": "Fashion Chatbot API", "status": "running"}

@api_router.post("/whatsapp/message", response_model=MessageResponse)
async def handle_whatsapp_message(message_data: WhatsAppMessage):
    """Procesa mensajes entrantes de WhatsApp"""
    try:
        logger.info(f"Received message from {message_data.phone_number}: {message_data.message}")
        
        result = await chatbot_service.process_message(
            phone_number=message_data.phone_number,
            message_text=message_data.message,
            image_base64=message_data.image_base64
        )
        
        return MessageResponse(
            success=result["success"],
            reply=result["reply"]
        )
        
    except Exception as e:
        logger.error(f"Error handling WhatsApp message: {str(e)}")
        return MessageResponse(
            success=False,
            reply="Disculpa, tuve un problema. Por favor intenta de nuevo."
        )

@api_router.get("/conversations")
async def get_conversations(limit: int = 20, skip: int = 0):
    """Obtiene lista de conversaciones"""
    try:
        conversations = await db.conversations.find(
            {},
            {"_id": 0}
        ).sort("updated_at", -1).skip(skip).limit(limit).to_list(length=limit)
        
        return {"conversations": conversations, "total": len(conversations)}
        
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/conversations/{phone_number}")
async def get_conversation(phone_number: str):
    """Obtiene una conversación específica"""
    try:
        conversation = await db.conversations.find_one(
            {"phone_number": phone_number},
            {"_id": 0}
        )
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return conversation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/products/popular")
async def get_popular_products(limit: int = 10):
    """Obtiene productos más buscados"""
    try:
        products = await db.products.find(
            {},
            {"_id": 0}
        ).sort("search_count", -1).limit(limit).to_list(length=limit)
        
        return {"products": products}
        
    except Exception as e:
        logger.error(f"Error getting popular products: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Obtiene estadísticas del dashboard"""
    try:
        # Total de conversaciones
        total_conversations = await db.conversations.count_documents({})
        
        # Conversaciones activas (actualizadas en las últimas 24 horas)
        yesterday = datetime.utcnow() - timedelta(days=1)
        active_conversations = await db.conversations.count_documents({
            "updated_at": {"$gte": yesterday}
        })
        
        # Total de productos buscados
        products_stats = await db.products.aggregate([
            {"$group": {"_id": None, "total": {"$sum": "$search_count"}}}
        ]).to_list(length=1)
        total_products_searched = products_stats[0]["total"] if products_stats else 0
        
        # Total de órdenes
        total_orders = await db.orders.count_documents({})
        
        # Revenue hoy (simulado por ahora)
        revenue_today = 0.0
        
        return DashboardStats(
            total_conversations=total_conversations,
            active_conversations=active_conversations,
            total_products_searched=total_products_searched,
            total_orders=total_orders,
            revenue_today=revenue_today
        )
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/products/sync")
async def sync_products():
    """Sincroniza productos de WooCommerce"""
    try:
        products = await woocommerce_service.get_featured_products(limit=20)
        
        # Guardar en cache
        for product in products:
            await db.products.update_one(
                {"wc_id": product["wc_id"]},
                {"$set": product},
                upsert=True
            )
        
        return {"success": True, "synced": len(products)}
        
    except Exception as e:
        logger.error(f"Error syncing products: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/products/search-by-image")
async def search_products_by_image(request: Request):
    """Busca productos por similitud visual usando embeddings"""
    try:
        data = await request.json()
        image_base64 = data.get('image_base64')
        
        if not image_base64:
            raise HTTPException(status_code=400, detail="image_base64 is required")
        
        # Buscar productos similares
        similar_products = await vector_search_service.search_by_image(image_base64, top_k=5)
        
        if not similar_products:
            return {"success": False, "products": [], "message": "No se encontraron productos similares"}
        
        # Enriquecer con datos de MongoDB
        product_ids = [p['wc_id'] for p in similar_products]
        mongo_products = await db.product_embeddings.find(
            {"wc_id": {"$in": product_ids}},
            {"_id": 0}
        ).to_list(length=len(product_ids))
        
        # Combinar datos
        enriched_products = []
        for similar in similar_products:
            mongo_data = next((p for p in mongo_products if p['wc_id'] == similar['wc_id']), None)
            if mongo_data:
                enriched_products.append({
                    **mongo_data,
                    'similarity_score': similar['similarity']
                })
        
        return {
            "success": True,
            "products": enriched_products,
            "count": len(enriched_products)
        }
        
    except Exception as e:
        logger.error(f"Error in image search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/products/indexed-count")
async def get_indexed_count():
    """Obtiene el número de productos indexados"""
    try:
        mongo_count = await db.product_embeddings.count_documents({})
        return {
            "mongodb": mongo_count,
            "status": "indexing" if mongo_count < 300 else "complete"
        }
    except Exception as e:
        logger.error(f"Error getting count: {str(e)}")
        return {"mongodb": 0, "status": "error"}

# Watermark endpoints
from services.watermark_service import watermark_service

@api_router.post("/watermark/encode")
async def encode_watermark(request: Request):
    """
    Incrusta IDs de productos en una imagen (watermark invisible)
    Body: { "image_base64": "...", "product_ids": [24112, 24150] }
    Returns: { "image_base64": "..." } con watermark
    """
    try:
        data = await request.json()
        image_base64 = data.get('image_base64')
        product_ids = data.get('product_ids', [])
        
        if not image_base64 or not product_ids:
            raise HTTPException(status_code=400, detail="image_base64 and product_ids required")
        
        # Aplicar watermark
        encoded_image = watermark_service.encode_image_base64(image_base64, product_ids)
        
        return {
            "success": True,
            "image_base64": encoded_image,
            "products_encoded": product_ids
        }
    except Exception as e:
        logger.error(f"Error encoding watermark: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/watermark/decode")
async def decode_watermark(request: Request):
    """
    Extrae IDs de productos de una imagen con watermark
    Body: { "image_base64": "..." }
    Returns: { "product_ids": [24112, 24150] }
    """
    try:
        data = await request.json()
        image_base64 = data.get('image_base64')
        
        if not image_base64:
            raise HTTPException(status_code=400, detail="image_base64 required")
        
        # Extraer watermark
        product_ids = watermark_service.decode_products(image_base64)
        
        return {
            "success": len(product_ids) > 0,
            "product_ids": product_ids
        }
    except Exception as e:
        logger.error(f"Error decoding watermark: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# WhatsApp Twilio Integration (Optional)
twilio_account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
twilio_auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
twilio_client = None
twilio_validator = None

from twilio.twiml.messaging_response import MessagingResponse

if twilio_account_sid and twilio_auth_token:
    try:
        from twilio.rest import Client
        from twilio.request_validator import RequestValidator
        twilio_client = Client(twilio_account_sid, twilio_auth_token)
        twilio_validator = RequestValidator(twilio_auth_token)
        logger.info("Twilio client initialized")
    except Exception as e:
        logger.error(f"Error initializing Twilio: {str(e)}")
else:
    logger.info("Twilio credentials not found, skipping initialization")

@api_router.post("/whatsapp/webhook")
async def receive_whatsapp_message(request: Request):
    """Recibe mensajes entrantes de WhatsApp vía Twilio"""
    try:
        # Obtener todos los datos del form
        form_data = await request.form()
        
        # Extraer campos
        From = form_data.get("From", "")
        Body = form_data.get("Body", "")
        NumMedia = int(form_data.get("NumMedia", 0))
        
        # Log completo para debug
        logger.info(f"Webhook received from {From}")
        logger.info(f"Body: {Body}")
        logger.info(f"NumMedia: {NumMedia}")
        logger.info(f"Form data keys: {list(form_data.keys())}")
        
        if not From:
            return Response(content="<?xml version='1.0' encoding='UTF-8'?><Response></Response>", media_type="application/xml")
        
        # Extraer número de teléfono
        phone_number = From.replace("whatsapp:", "")
        
        # Procesar imágenes si existen
        image_base64 = None
        if NumMedia > 0:
            logger.info(f"Processing {NumMedia} media files")
            media_url = form_data.get("MediaUrl0")
            logger.info(f"MediaUrl0: {media_url}")
            
            if media_url:
                # Descargar imagen y convertir a base64
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    media_response = await client.get(
                        media_url,
                        auth=(os.environ.get('TWILIO_ACCOUNT_SID'), os.environ.get('TWILIO_AUTH_TOKEN')),
                        timeout=30.0
                    )
                    if media_response.status_code == 200:
                        import base64
                        image_base64 = base64.b64encode(media_response.content).decode('utf-8')
                        logger.info(f"✓ Image downloaded successfully, size: {len(image_base64)}")
                    else:
                        logger.error(f"Failed to download media: {media_response.status_code}")
        else:
            logger.info("No media in message")
        
        # Procesar mensaje con el chatbot
        result = await chatbot_service.process_message(
            phone_number=phone_number,
            message_text=Body if Body else "imagen",
            image_base64=image_base64
        )
        
        # Enviar respuesta
        if result["success"] and result["reply"]:
            await send_whatsapp_message(phone_number, result["reply"])
        
        # Responder a Twilio con TwiML vacío
        response = MessagingResponse()
        return Response(content=str(response), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error in WhatsApp webhook: {str(e)}")
        response = MessagingResponse()
        return Response(content=str(response), media_type="application/xml")

async def send_whatsapp_message(to_number: str, message: str):
    """Envía un mensaje de WhatsApp usando Twilio"""
    try:
        twilio_number = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
        
        message = twilio_client.messages.create(
            from_=twilio_number,
            to=f"whatsapp:{to_number}",
            body=message
        )
        
        logger.info(f"Message sent to {to_number}: {message.sid}")
        return {"success": True, "message_sid": message.sid}
        
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {str(e)}")
        return {"success": False, "error": str(e)}

# Meta WhatsApp Cloud API Integration
@api_router.get("/meta/webhook")
async def verify_meta_webhook(request: Request):
    """Verificación del webhook por parte de Meta"""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    verify_token = os.environ.get("META_WHATSAPP_VERIFY_TOKEN", "WinstonHarry2024")
    
    if mode == "subscribe" and token == verify_token:
        logger.info("Meta Webhook verified successfully")
        return Response(content=challenge)
    
    logger.warning("Meta Webhook verification failed")
    return Response(content="Verification failed", status_code=403)

@api_router.post("/meta/webhook")
async def receive_meta_message(request: Request):
    """Recibe notificaciones de mensajes desde Meta"""
    try:
        body = await request.json()
        logger.info(f"Meta Webhook received: {body}")
        
        # Validar estructura básica de Meta
        if not body.get("entry") or not body["entry"][0].get("changes"):
            return {"status": "ok"}
            
        change = body["entry"][0]["changes"][0]["value"]
        logger.info(f"Change value: {change}")
        
        if "messages" not in change:
            logger.info("No messages in change, ignoring (probably a status update)")
            return {"status": "ok"}
            
        message = change["messages"][0]
        phone_number = message["from"]
        msg_type = message["type"]
        
        message_text = ""
        image_base64 = None
        
        if msg_type == "text":
            message_text = message["text"]["body"]
        elif msg_type == "image":
            message_text = message.get("image", {}).get("caption", "") or "imagen"
            media_id = message["image"]["id"]
            image_base64 = await download_meta_media(media_id)
        
        if not message_text and not image_base64:
            return {"status": "ok"}
            
        # Procesar con el chatbot
        result = await chatbot_service.process_message(
            phone_number=phone_number,
            message_text=message_text,
            image_base64=image_base64
        )
        
        # Enviar respuesta vía Meta
        if result["success"] and result["reply"]:
            await meta_whatsapp_service.send_message(phone_number, result["reply"])
            
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing Meta webhook: {str(e)}")
        return {"status": "error", "message": str(e)}

async def download_meta_media(media_id: str) -> Optional[str]:
    """Descarga multimedia de los servidores de Meta y lo convierte a base64"""
    try:
        access_token = os.environ.get('META_WHATSAPP_ACCESS_TOKEN')
        api_version = os.environ.get('META_WHATSAPP_API_VERSION', 'v21.0')
        
        async with httpx.AsyncClient() as client:
            # 1. Obtener URL de descarga
            get_url = f"https://graph.facebook.com/{api_version}/{media_id}"
            headers = {"Authorization": f"Bearer {access_token}"}
            
            response = await client.get(get_url, headers=headers)
            if response.status_code != 200:
                return None
                
            download_url = response.json().get("url")
            if not download_url:
                return None
                
            # 2. Descargar el archivo
            file_response = await client.get(download_url, headers=headers)
            if file_response.status_code == 200:
                import base64
                return base64.b64encode(file_response.content).decode('utf-8')
                
        return None
    except Exception as e:
        logger.error(f"Error downloading Meta media: {str(e)}")
        return None

@api_router.get("/whatsapp/status")
async def get_whatsapp_status():
    """Obtiene el estado de la conexión de WhatsApp"""
    return {
        "connected": True,
        "provider": "meta_cloud_api",
        "phone_number_id": os.environ.get('META_WHATSAPP_PHONE_NUMBER_ID')
    }

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()