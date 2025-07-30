import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.core.cache import cache
from .models import ChatMessage

class PracownicyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = 'pracownicy_updates'
        self.room_group_name = f'pracownicy_{self.room_name}'

        # Dodaj do grupy
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        
        # Wyślij wiadomość powitalną
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Połączono z systemem powiadomień!'
        }))

        # Wyślij historię czatu
        chat_history = await self.get_chat_history()
        await self.send(text_data=json.dumps({
            'type': 'chat_history',
            'messages': chat_history
        }))

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
        
        # Pobierz username
        user = self.scope.get('user')
        if user and user.is_authenticated:
            self.username = user.username
        else:
            self.username = f"Gość_{self.channel_name[-8:]}"

        # Dodaj do grupy
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Dodaj do listy uczestników w cache
        participants_key = f"room_participants_{self.room_name}"
        participants = cache.get(participants_key, set())
        participants.add(self.username)
        cache.set(participants_key, participants, 3600)  # 1 godzina
        
        await self.accept()
        
        # Powiadom wszystkich o nowym użytkowniku
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'username': self.username,
                'participants': list(participants)
            }
        )

    async def disconnect(self, close_code):
        # Usuń z listy uczestników w cache
        participants_key = f"room_participants_{self.room_name}"
        participants = cache.get(participants_key, set())
        participants.discard(self.username)
        
        if participants:
            cache.set(participants_key, participants, 3600)
        else:
            cache.delete(participants_key)
        
        # Powiadom wszystkich o opuszczeniu
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'username': self.username,
                'participants': list(participants)
            }
        )
        
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            
            # Dodaj informację o nadawcy do wiadomości
            data['from'] = self.username
            
            # Przekaż sygnały WebRTC do wszystkich uczestników
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'signal_message',
                    'message': json.dumps(data),
                    'sender': self.channel_name
                }
            )
        except json.JSONDecodeError:
            # Fallback dla surowych danych - dodaj username
            fallback_data = {
                'raw_data': text_data,
                'from': self.username
            }
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'signal_message',
                    'message': json.dumps(fallback_data),
                    'sender': self.channel_name
                }
            )

    async def signal_message(self, event):
        # Nie wysyłaj wiadomości z powrotem do nadawcy
        if event.get('sender') != self.channel_name:
            await self.send(text_data=event['message'])

    async def user_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'username': event['username'],
            'participants': event['participants']
        }))

    async def user_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'username': event['username'],
            'participants': event['participants']
        }))