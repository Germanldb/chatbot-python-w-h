const { makeWASocket, useMultiFileAuthState, DisconnectReason, delay } = require('@whiskeysockets/baileys')
const qrcode = require('qrcode-terminal')
const express = require('express')
const cors = require('cors')
const axios = require('axios')
require('dotenv').config()

const app = express()
app.use(cors())
app.use(express.json({ limit: '50mb' }))

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000'
const PORT = process.env.PORT || 3001

let sock = null
let qrData = null
let connectionStatus = 'disconnected'

// Inicializar WhatsApp
async function initWhatsApp() {
    try {
        const { state, saveCreds } = await useMultiFileAuthState('./auth_info')

        sock = makeWASocket({
            auth: state,
            printQRInTerminal: false,
            browser: ['Fashion Assistant', 'Chrome', '1.0.0']
        })

        sock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update

            if (qr) {
                qrData = qr
                qrcode.generate(qr, { small: true })
                console.log('QR Code generado. Escánealo con WhatsApp.')
            }

            if (connection === 'close') {
                const shouldReconnect = lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut
                console.log('Conexión cerrada. Reconectando:', shouldReconnect)
                connectionStatus = 'disconnected'
                
                if (shouldReconnect) {
                    await delay(5000)
                    initWhatsApp()
                }
            } else if (connection === 'open') {
                console.log('WhatsApp conectado exitosamente!')
                connectionStatus = 'connected'
                qrData = null
            }
        })

        sock.ev.on('messages.upsert', async ({ messages, type }) => {
            if (type === 'notify') {
                for (const message of messages) {
                    if (!message.key.fromMe && message.message) {
                        await handleIncomingMessage(message)
                    }
                }
            }
        })

        sock.ev.on('creds.update', saveCreds)

    } catch (error) {
        console.error('Error inicializando WhatsApp:', error)
        connectionStatus = 'error'
        await delay(10000)
        initWhatsApp()
    }
}

async function handleIncomingMessage(message) {
    try {
        const phoneNumber = message.key.remoteJid.replace('@s.whatsapp.net', '')
        let messageText = ''
        let imageBase64 = null

        // Extraer texto del mensaje
        if (message.message.conversation) {
            messageText = message.message.conversation
        } else if (message.message.extendedTextMessage) {
            messageText = message.message.extendedTextMessage.text
        }

        // Extraer imagen si existe
        if (message.message.imageMessage) {
            try {
                const buffer = await downloadMediaMessage(
                    message,
                    'buffer',
                    {},
                    {
                        logger: console,
                        reuploadRequest: sock.updateMediaMessage
                    }
                )
                imageBase64 = buffer.toString('base64')
                messageText = message.message.imageMessage.caption || 'Imagen enviada'
            } catch (error) {
                console.error('Error descargando imagen:', error)
            }
        }

        console.log(`Mensaje de ${phoneNumber}: ${messageText}`)

        // Enviar al backend de FastAPI
        const response = await axios.post(`${FASTAPI_URL}/api/whatsapp/message`, {
            phone_number: phoneNumber,
            message: messageText,
            message_id: message.key.id,
            timestamp: message.messageTimestamp,
            image_base64: imageBase64
        })

        // Enviar respuesta a WhatsApp
        if (response.data.reply) {
            await sendMessage(phoneNumber, response.data.reply)
        }

    } catch (error) {
        console.error('Error manejando mensaje:', error)
        // Enviar mensaje de error al usuario
        try {
            const phoneNumber = message.key.remoteJid.replace('@s.whatsapp.net', '')
            await sendMessage(phoneNumber, 'Disculpa, tuve un problema procesando tu mensaje. ¿Podrías intentar de nuevo?')
        } catch (e) {
            console.error('Error enviando mensaje de error:', e)
        }
    }
}

async function downloadMediaMessage(message, type, options, ctx) {
    const stream = await require('@whiskeysockets/baileys').downloadContentFromMessage(
        message.message.imageMessage,
        'image'
    )
    
    let buffer = Buffer.from([])
    for await (const chunk of stream) {
        buffer = Buffer.concat([buffer, chunk])
    }
    
    return buffer
}

async function sendMessage(phoneNumber, text) {
    try {
        if (!sock) {
            throw new Error('WhatsApp no está conectado')
        }

        const jid = phoneNumber.includes('@') ? phoneNumber : `${phoneNumber}@s.whatsapp.net`
        await sock.sendMessage(jid, { text })
        console.log(`Mensaje enviado a ${phoneNumber}`)
        return { success: true }

    } catch (error) {
        console.error('Error enviando mensaje:', error)
        return { success: false, error: error.message }
    }
}

// REST API Endpoints
app.get('/qr', (req, res) => {
    res.json({ qr: qrData || null })
})

app.post('/send', async (req, res) => {
    const { phone_number, message } = req.body
    const result = await sendMessage(phone_number, message)
    res.json(result)
})

app.get('/status', (req, res) => {
    res.json({
        connected: connectionStatus === 'connected',
        status: connectionStatus,
        user: sock?.user || null
    })
})

app.get('/health', (req, res) => {
    res.json({ status: 'ok', service: 'whatsapp', uptime: process.uptime() })
})

// Iniciar servidor
app.listen(PORT, () => {
    console.log(`WhatsApp service ejecutándose en puerto ${PORT}`)
    initWhatsApp()
})

// Manejo de señales
process.on('SIGINT', async () => {
    console.log('\nCerrando servicio...')
    if (sock) {
        await sock.logout()
    }
    process.exit(0)
})