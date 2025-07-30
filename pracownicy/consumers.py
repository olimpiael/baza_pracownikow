import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.utils import timezone
from .models import ChatMessage

class PracownicyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = 'pracownicy_updates'
        self.room_group_name = f'pracownicy_{self.room_name}'

        try:
            # Dodaj do grupy
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            await self.accept()
            
            # Wyślij wiadomość powitalną
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Połączono z systemem powiadomień!',
                'server_time': str(timezone.now())
            }))

            # Wyślij historię czatu
            chat_history = await self.get_chat_history()
            await self.send(text_data=json.dumps({
                'type': 'chat_history',
                'messages': chat_history
            }))
        except Exception as e:
            print(f"Error in WebSocket connect: {e}")
            await self.close()

    async def disconnect(self, close_code):
        # Usuń z grupy
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type', '')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'message': 'Połączenie aktywne'
                }))
            
            elif message_type == 'broadcast_message':
                message = data.get('message', '')
                user_name = data.get('user_name', 'Anonimowy')
                user_id_str = data.get('user_id', '')
                
                # Zapisz wiadomość do bazy danych
                if user_id_str and user_id_str.isdigit() and message.strip():
                    user_id = int(user_id_str)
                    chat_message = await self.save_chat_message(user_id, message)
                    
                    if chat_message:
                        # Rozgłoś wiadomość do wszystkich w grupie
                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                'type': 'chat_message',
                                'message': message,
                                'user_name': chat_message.user_display_name,
                                'timestamp': chat_message.timestamp.strftime('%H:%M'),
                                'message_id': chat_message.id
                            }
                        )
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Nieprawidłowy format JSON'
            }))

    # Obsługa wiadomości czatu
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'user_name': event['user_name'],
            'timestamp': event['timestamp']
        }))

    # Obsługa powiadomień o zmianach w pracownikach
    async def employee_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'employee_update',
            'action': event['action'],
            'employee_id': event['employee_id'],
            'employee_name': event.get('employee_name', ''),
            'message': event['message']
        }))

    # Obsługa powiadomień systemowych
    async def system_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'system_notification',
            'message': event['message'],
            'level': event.get('level', 'info')
        }))

    # Funkcje pomocnicze do obsługi bazy danych
    @database_sync_to_async
    def save_chat_message(self, user_id, message):
        """Zapisuje wiadomość czatu do bazy danych"""
        try:
            user = User.objects.get(id=user_id)
            chat_message = ChatMessage.objects.create(
                user=user,
                message=message
            )
            return chat_message
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def get_chat_history(self, limit=50):
        """Pobiera historię czatu z bazy danych"""
        messages = ChatMessage.objects.filter(is_deleted=False)[:limit]
        history = []
        for msg in messages:
            history.append({
                'message': msg.message,
                'user_name': msg.user_display_name,
                'timestamp': msg.timestamp.strftime('%H:%M'),
                'message_id': msg.id
            })
        return list(reversed(history))  # Odwracamy kolejność, aby najnowsze były na końcu
    

class VoiceRoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"room_{self.room_name}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'signal_message',
                'message': text_data
            }
        )

    async def signal_message(self, event):
        await self.send(text_data=event['message'])