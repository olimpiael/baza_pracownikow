import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer

class SimpleVoiceRoomConsumer(AsyncWebsocketConsumer):
    """
    Prosty consumer dla testowania WebSocket na Railway
    """
    
    async def connect(self):
        print("SimpleVoiceRoomConsumer: Connect attempt")
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"room_{self.room_name}"
        
        try:
            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            await self.accept()
            print(f"SimpleVoiceRoomConsumer: Connected to room {self.room_name}")
            
            # Send welcome message
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': f'Connected to room {self.room_name}',
                'room': self.room_name
            }))
            
        except Exception as e:
            print(f"SimpleVoiceRoomConsumer: Error in connect: {e}")
            await self.close()

    async def disconnect(self, close_code):
        print(f"SimpleVoiceRoomConsumer: Disconnect from {self.room_name}, code: {close_code}")
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            print(f"SimpleVoiceRoomConsumer: Received data: {text_data[:100]}...")
            
            # Parse message
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', 'unknown')
            
            # Echo back to all in room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'room_message',
                    'message': text_data,
                    'sender_channel': self.channel_name
                }
            )
            
        except Exception as e:
            print(f"SimpleVoiceRoomConsumer: Error in receive: {e}")

    async def room_message(self, event):
        # Don't send back to sender
        if event.get('sender_channel') != self.channel_name:
            await self.send(text_data=event['message'])
