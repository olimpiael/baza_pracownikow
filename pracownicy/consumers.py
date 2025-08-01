import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.utils import timezone
from .models import ChatMessage

print("Loading consumers.py - imports successful")

class PracownicyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print("WebSocket: Attempting to connect")
        self.room_name = 'pracownicy_updates'
        self.room_group_name = f'pracownicy_{self.room_name}'

        try:
            # Sprawdź czy channel_layer jest dostępny
            if not hasattr(self, 'channel_layer') or self.channel_layer is None:
                print("WebSocket: Channel layer not available")
                await self.close()
                return
                
            # Dodaj do grupy
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            print("WebSocket: Added to group successfully")

            await self.accept()
            print("WebSocket: Connection accepted")
            
            # Wyślij wiadomość powitalną
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Połączono z systemem powiadomień!',
                'server_time': str(timezone.now())
            }))
            print("WebSocket: Welcome message sent")

            # Wyślij historię czatu
            chat_history = await self.get_chat_history()
            await self.send(text_data=json.dumps({
                'type': 'chat_history',
                'messages': chat_history
            }))
            print("WebSocket: Chat history sent")
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
        messages = ChatMessage.objects.filter(is_deleted=False).order_by('timestamp')[:limit]
        history = []
        for msg in messages:
            history.append({
                'message': msg.message,
                'user_name': msg.user_display_name,
                'timestamp': msg.timestamp.strftime('%H:%M'),
                'message_id': msg.id
            })
        return history  # Zwracamy w kolejności chronologicznej (najstarsze pierwsze)
    

class VoiceRoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print(f"VoiceRoom WebSocket: Attempting to connect from {self.scope.get('client', ['unknown', 'unknown'])[0]}")
        
        try:
            self.room_name = self.scope['url_route']['kwargs']['room_name']
            self.room_group_name = f"room_{self.room_name}"
            self.user = self.scope.get("user")
            
            print(f"VoiceRoom WebSocket: Room: {self.room_name}, User: {self.user}")
            
            # Sprawdź czy użytkownik jest zalogowany
            if not self.user or not self.user.is_authenticated:
                print("VoiceRoom WebSocket: User not authenticated")
                await self.close(code=4001)  # Custom close code
                return
                
            self.username = getattr(self.user, 'first_name', '') + ' ' + getattr(self.user, 'last_name', '')
            if not self.username.strip():
                self.username = self.user.username
                
            print(f"VoiceRoom WebSocket: User {self.username} connecting to room {self.room_name}")

            # Sprawdź czy channel_layer jest dostępny  
            if not hasattr(self, 'channel_layer') or self.channel_layer is None:
                print("VoiceRoom WebSocket: Channel layer not available")
                await self.close(code=4002)  # Custom close code
                return
                
            print(f"VoiceRoom WebSocket: Channel layer available: {type(self.channel_layer)}")
            
            # Dodaj do grupy
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            print(f"VoiceRoom WebSocket: Added to group {self.room_group_name}")
            
            await self.accept()
            print(f"VoiceRoom WebSocket: Connection accepted for {self.username}")
            
            # Powiadom innych o dołączeniu - bez lokalnego słownika
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_joined',
                    'username': self.username,
                }
            )
            print(f"VoiceRoom WebSocket: Sent user_joined event for {self.username}")
            
        except Exception as e:
            print(f"VoiceRoom WebSocket: Error in connect: {e}")
            import traceback
            traceback.print_exc()
            await self.close(code=4003)  # Custom close code

    async def disconnect(self, close_code):
        print(f"VoiceRoom WebSocket: {getattr(self, 'username', 'Unknown')} disconnecting from {getattr(self, 'room_name', 'Unknown')}, code: {close_code}")
        
        try:
            # Usuń z grupy
            if hasattr(self, 'room_group_name') and hasattr(self, 'channel_name'):
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
                print(f"VoiceRoom WebSocket: Removed from group {self.room_group_name}")
            
            # Powiadom innych o opuszczeniu - bez lokalnego słownika
            if hasattr(self, 'room_group_name') and hasattr(self, 'username'):
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'user_left',
                        'username': self.username,
                    }
                )
                print(f"VoiceRoom WebSocket: Sent user_left event for {self.username}")
        except Exception as e:
            print(f"VoiceRoom WebSocket: Error in disconnect: {e}")
            import traceback
            traceback.print_exc()

    async def receive(self, text_data):
        try:
            print(f"VoiceRoom WebSocket: Received data from {self.username}: {text_data[:100]}...")
            
            # Sprawdź czy to ping/pong
            try:
                data = json.loads(text_data)
                if data.get('type') == 'ping':
                    await self.send(text_data=json.dumps({
                        'type': 'pong',
                        'timestamp': data.get('timestamp')
                    }))
                    print(f"VoiceRoom WebSocket: Sent pong to {self.username}")
                    return
            except json.JSONDecodeError:
                pass  # Nie JSON, kontynuuj jako sygnał WebRTC
            
            # Przekaż sygnał do wszystkich w pokoju
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'signal_message',
                    'message': text_data,
                    'sender': self.username
                }
            )
        except Exception as e:
            print(f"VoiceRoom WebSocket: Error in receive: {e}")

    async def signal_message(self, event):
        # Nie wysyłaj sygnału z powrotem do nadawcy
        if event.get('sender') != self.username:
            await self.send(text_data=event['message'])
    
    async def user_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'username': event['username'],
        }))
    
    async def user_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'username': event['username'], 
        }))