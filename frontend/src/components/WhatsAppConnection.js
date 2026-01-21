import React from 'react';
import { useWhatsAppConnection } from '../hooks/useApi';
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { CheckCircle2, Loader2, XCircle, Smartphone, MessageSquare } from 'lucide-react';

export function WhatsAppConnection() {
  const { isConnected, status, loading } = useWhatsAppConnection();
  const sandboxNumber = '+14155238886';
  const joinCode = 'join top-whale';

  return (
    <div className="w-full max-w-3xl mx-auto p-6" data-testid="whatsapp-connection">
      <Card className="border-border">
        <CardHeader>
          <CardTitle className="text-3xl font-heading font-bold tracking-tight">
            Conexión WhatsApp (Twilio)
          </CardTitle>
          <CardDescription>
            Conecta tu WhatsApp usando Twilio Sandbox para comenzar a atender clientes
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Status Badge */}
          <div className="flex items-center justify-center space-x-3">
            {status === 'connected' && (
              <div className="flex items-center space-x-2 px-4 py-2 bg-primary/10 text-primary rounded-full" data-testid="status-connected">
                <CheckCircle2 className="w-5 h-5" />
                <span className="font-medium">Conectado - Twilio Activo</span>
              </div>
            )}
            {status === 'disconnected' && (
              <div className="flex items-center space-x-2 px-4 py-2 bg-muted text-muted-foreground rounded-full" data-testid="status-disconnected">
                <XCircle className="w-5 h-5" />
                <span className="font-medium">Configurar Sandbox</span>
              </div>
            )}
            {status === 'error' && (
              <div className="flex items-center space-x-2 px-4 py-2 bg-destructive/10 text-destructive rounded-full" data-testid="status-error">
                <XCircle className="w-5 h-5" />
                <span className="font-medium">Error de conexión</span>
              </div>
            )}\n          </div>

          {/* Twilio Setup Instructions */}
          <div className="space-y-6" data-testid="twilio-instructions">
            <div className="bg-accent/10 border-2 border-accent rounded-lg p-6">
              <h3 className="text-xl font-heading font-semibold mb-4 flex items-center">
                <MessageSquare className="w-6 h-6 mr-2 text-accent-foreground" />
                Configuración de Twilio Sandbox
              </h3>
              
              <div className="space-y-4">
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-primary text-primary-foreground rounded-full flex items-center justify-center font-bold">
                    1
                  </div>
                  <div className="flex-1">
                    <p className="font-medium mb-1">Envía un mensaje de WhatsApp</p>
                    <p className="text-sm text-muted-foreground">
                      Abre WhatsApp y envía el siguiente mensaje a:{' '}
                      <span className="font-mono bg-muted px-2 py-1 rounded">{sandboxNumber}</span>
                    </p>
                  </div>
                </div>

                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-primary text-primary-foreground rounded-full flex items-center justify-center font-bold">
                    2
                  </div>
                  <div className="flex-1">
                    <p className="font-medium mb-2">Usa este código para unirte:</p>
                    <div className="bg-primary/10 border border-primary rounded-lg p-4 text-center">
                      <code className="text-2xl font-mono font-bold text-primary">
                        {joinCode}
                      </code>
                    </div>
                  </div>
                </div>

                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-primary text-primary-foreground rounded-full flex items-center justify-center font-bold">
                    3
                  </div>
                  <div className="flex-1">
                    <p className="font-medium mb-1">¡Listo!</p>
                    <p className="text-sm text-muted-foreground">
                      Recibirás un mensaje de confirmación. Ahora puedes enviar fotos de productos 
                      y el bot responderá automáticamente.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Testing Instructions */}
            <div className="bg-muted/50 rounded-lg p-6">
              <h4 className="font-heading font-semibold mb-3">💡 Prueba el Chatbot</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>• Envía una foto de zapatos o ropa para buscar productos similares</li>
                <li>• Escribe "Hola" para iniciar una conversación</li>
                <li>• Pregunta por consejos de moda: "¿Cómo combino esta camisa?"</li>
                <li>• Pide información sobre productos específicos</li>
              </ul>
            </div>

            {/* Webhook Configuration */}
            <div className="bg-muted rounded-lg p-6">
              <h4 className="font-heading font-semibold mb-3">🔧 Configuración del Webhook</h4>
              <p className="text-sm text-muted-foreground mb-3">
                En tu Twilio Console, configura el webhook para recibir mensajes:
              </p>
              <div className="bg-background rounded border p-3">
                <p className="text-xs font-mono break-all">
                  https://smartshopper-60.preview.emergentagent.com/api/whatsapp/webhook
                </p>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                * Twilio → Messaging → Settings → WhatsApp Sandbox → "When a message comes in"
              </p>
            </div>
          </div>

          {/* Connected State */}
          {isConnected && (
            <div className="text-center space-y-4 bg-primary/5 rounded-lg p-6" data-testid="connected-state">
              <div className="flex justify-center">
                <div className="p-6 bg-primary/10 rounded-full">
                  <Smartphone className="w-16 h-16 text-primary" />
                </div>
              </div>
              <div>
                <h3 className="text-xl font-heading font-semibold mb-2 text-primary">
                  ¡Bot Activo!</h3>
                <p className="text-muted-foreground">
                  Tu chatbot de moda está funcionando y listo para recibir mensajes de clientes.
                </p>
              </div>
            </div>
          )}

          {/* Loading State */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-12 space-y-4" data-testid="loading-state">
              <Loader2 className="w-12 h-12 text-primary animate-spin" />
              <p className="text-muted-foreground">Verificando conexión...</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}