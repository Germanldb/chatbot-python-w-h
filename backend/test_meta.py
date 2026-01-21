import asyncio
import os
from dotenv import load_dotenv
import httpx

async def test_meta_connection():
    load_dotenv()
    
    access_token = os.getenv('META_WHATSAPP_ACCESS_TOKEN')
    phone_number_id = os.getenv('META_WHATSAPP_PHONE_NUMBER_ID')
    version = os.getenv('META_WHATSAPP_API_VERSION', 'v22.0')
    
    print(f"--- Probando Conexión Meta ---")
    print(f"Phone Number ID: {phone_number_id}")
    print(f"Versión: {version}")
    
    if not access_token or not phone_number_id:
        print("Error: Faltan credenciales en el .env")
        return

    url = f"https://graph.facebook.com/{version}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Intentamos enviar un mensaje de prueba a un número (puedes cambiarlo)
    payload = {
        "messaging_product": "whatsapp",
        "to": "584245594122", # El número que pusiste en el ejemplo
        "type": "text",
        "text": {"body": "✅ ¡Hola! El chatbot de Winston & Harry ya está conectado a la API de Meta."}
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            print(f"Status: {response.status_code}")
            print(f"Respuesta: {response.text}")
            
            if response.status_code == 200:
                print("\n✅ ¡ÉXITO! Las credenciales son correctas.")
            else:
                print("\n❌ Error en las credenciales. Revisa el Access Token o el ID.")
        except Exception as e:
            print(f"\n❌ Error de conexión: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_meta_connection())
