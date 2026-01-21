import React, { useState } from 'react';
import { useConversations, useConversation } from '../hooks/useApi';
import { Card } from './ui/card';
import { Input } from './ui/input';
import { ScrollArea } from './ui/scroll-area';
import { Avatar } from './ui/avatar';
import { Search, Phone, Clock, Loader2 } from 'lucide-react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

export function ChatPanel() {
  const { conversations, loading } = useConversations();
  const [selectedPhone, setSelectedPhone] = useState(null);
  const { conversation, loading: loadingConversation } = useConversation(selectedPhone);
  const [searchQuery, setSearchQuery] = useState('');

  const filteredConversations = conversations.filter(conv => 
    conv.phone_number.includes(searchQuery) || 
    conv.customer_name?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="chat-layout" data-testid="chat-panel">
      {/* Conversations List */}
      <div className="border-r border-border bg-card">
        <div className="p-4 border-b border-border">
          <h2 className="text-2xl font-heading font-semibold mb-4">Conversaciones</h2>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
            <Input
              placeholder="Buscar conversaciones..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
              data-testid="search-conversations"
            />
          </div>
        </div>

        <ScrollArea className="h-[calc(100vh-12rem)]">
          {loading ? (
            <div className="flex items-center justify-center p-8">
              <Loader2 className="w-8 h-8 text-primary animate-spin" />
            </div>
          ) : filteredConversations.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              <p>No hay conversaciones aún</p>
            </div>
          ) : (
            filteredConversations.map((conv) => (
              <div
                key={conv.phone_number}
                className={`conversation-item ${selectedPhone === conv.phone_number ? 'active' : ''}`}
                onClick={() => setSelectedPhone(conv.phone_number)}
                data-testid={`conversation-${conv.phone_number}`}
              >
                <div className="flex items-start space-x-3">
                  <Avatar className="w-10 h-10 bg-primary/10 flex items-center justify-center">
                    <Phone className="w-5 h-5 text-primary" />
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <p className="font-medium text-sm truncate">
                        {conv.customer_name || conv.phone_number}
                      </p>
                      <span className="text-xs text-muted-foreground flex items-center">
                        <Clock className="w-3 h-3 mr-1" />
                        {format(new Date(conv.updated_at), 'HH:mm', { locale: es })}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground truncate">
                      {conv.messages[conv.messages.length - 1]?.content || 'Sin mensajes'}
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </ScrollArea>
      </div>

      {/* Chat Area */}
      <div className="bg-muted/30">
        {selectedPhone ? (
          <div className="h-full flex flex-col">
            {/* Chat Header */}
            <div className="p-4 bg-card border-b border-border">
              <div className="flex items-center space-x-3">
                <Avatar className="w-10 h-10 bg-primary/10 flex items-center justify-center">
                  <Phone className="w-5 h-5 text-primary" />
                </Avatar>
                <div>
                  <p className="font-medium">
                    {conversation?.customer_name || selectedPhone}
                  </p>
                  <p className="text-sm text-muted-foreground">{selectedPhone}</p>
                </div>
              </div>
            </div>

            {/* Messages */}
            <ScrollArea className="flex-1 p-4">
              {loadingConversation ? (
                <div className="flex items-center justify-center h-full">
                  <Loader2 className="w-8 h-8 text-primary animate-spin" />
                </div>
              ) : conversation?.messages?.length > 0 ? (
                <div className="space-y-4">
                  {conversation.messages.map((message, index) => (
                    <div
                      key={index}
                      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      data-testid={`message-${index}`}
                    >
                      <div className={`message-bubble ${message.role}`}>
                        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                        {message.image_url && (
                          <img
                            src={message.image_url}
                            alt="Imagen enviada"
                            className="mt-2 rounded-lg max-w-xs"
                          />
                        )}
                        <p className="text-xs opacity-70 mt-1">
                          {format(new Date(message.timestamp), 'HH:mm', { locale: es })}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  <p>No hay mensajes en esta conversación</p>
                </div>
              )}
            </ScrollArea>

            {/* Input Area */}
            <div className="p-4 bg-card border-t border-border">
              <p className="text-sm text-muted-foreground text-center">
                Los mensajes se envían automáticamente desde WhatsApp
              </p>
            </div>
          </div>
        ) : (
          <div className="h-full flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <MessageSquare className="w-16 h-16 mx-auto mb-4 opacity-20" />
              <p>Selecciona una conversación para ver los mensajes</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function MessageSquare({ className }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}