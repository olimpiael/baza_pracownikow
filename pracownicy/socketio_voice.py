import socketio
import json
import time
from django.contrib.auth.models import User
import base64
import uuid

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins="*",
    ping_timeout=60,
    ping_interval=25,
    logger=True,
    engineio_logger=True
)

# Voice rooms storage
voice_rooms_socketio = {}

@sio.event
async def connect(sid, environ, auth):
    """Handle client connection"""
    print(f"Socket.IO: Client {sid} connected")
    await sio.emit('connected', {'status': 'connected', 'sid': sid}, room=sid)

@sio.event
async def disconnect(sid):
    """Handle client disconnection"""
    print(f"Socket.IO: Client {sid} disconnected")
    
    # Remove from all rooms
    for room_id in list(voice_rooms_socketio.keys()):
        if sid in voice_rooms_socketio[room_id]['participants']:
            voice_rooms_socketio[room_id]['participants'].discard(sid)
            await sio.emit('user_left', {
                'sid': sid,
                'participants': len(voice_rooms_socketio[room_id]['participants'])
            }, room=room_id)
            
            # Clean up empty rooms
            if not voice_rooms_socketio[room_id]['participants']:
                del voice_rooms_socketio[room_id]

@sio.event
async def join_voice_room(sid, data):
    """Join voice room"""
    try:
        room_id = data.get('room_id')
        username = data.get('username', f'User_{sid[:8]}')
        
        if not room_id:
            await sio.emit('error', {'message': 'Missing room_id'}, room=sid)
            return
        
        # Initialize room
        if room_id not in voice_rooms_socketio:
            voice_rooms_socketio[room_id] = {
                'participants': set(),
                'messages': []
            }
        
        # Add to room
        await sio.enter_room(sid, room_id)
        voice_rooms_socketio[room_id]['participants'].add(sid)
        
        # Notify room
        await sio.emit('user_joined', {
            'sid': sid,
            'username': username,
            'participants': len(voice_rooms_socketio[room_id]['participants'])
        }, room=room_id)
        
        # Confirm to user
        await sio.emit('room_joined', {
            'room_id': room_id,
            'participants': len(voice_rooms_socketio[room_id]['participants'])
        }, room=sid)
        
        print(f"Socket.IO: {sid} joined room {room_id}")
        
    except Exception as e:
        print(f"Socket.IO: Error in join_voice_room: {e}")
        await sio.emit('error', {'message': str(e)}, room=sid)

@sio.event
async def leave_voice_room(sid, data):
    """Leave voice room"""
    try:
        room_id = data.get('room_id')
        
        if room_id and room_id in voice_rooms_socketio:
            voice_rooms_socketio[room_id]['participants'].discard(sid)
            await sio.leave_room(sid, room_id)
            
            # Notify room
            await sio.emit('user_left', {
                'sid': sid,
                'participants': len(voice_rooms_socketio[room_id]['participants'])
            }, room=room_id)
            
            # Clean up empty rooms
            if not voice_rooms_socketio[room_id]['participants']:
                del voice_rooms_socketio[room_id]
        
        await sio.emit('room_left', {'room_id': room_id}, room=sid)
        
    except Exception as e:
        print(f"Socket.IO: Error in leave_voice_room: {e}")

@sio.event
async def send_audio(sid, data):
    """Send audio chunk to room"""
    try:
        room_id = data.get('room_id')
        audio_chunk = data.get('audio_chunk')
        username = data.get('username', f'User_{sid[:8]}')
        
        if not room_id or not audio_chunk:
            await sio.emit('error', {'message': 'Missing room_id or audio_chunk'}, room=sid)
            return
        
        if room_id not in voice_rooms_socketio:
            await sio.emit('error', {'message': 'Room not found'}, room=sid)
            return
        
        # Create message
        message = {
            'id': str(uuid.uuid4()),
            'type': 'audio',
            'sid': sid,
            'username': username,
            'audio_chunk': audio_chunk,
            'timestamp': time.time()
        }
        
        # Store message (keep last 20)
        voice_rooms_socketio[room_id]['messages'].append(message)
        if len(voice_rooms_socketio[room_id]['messages']) > 20:
            voice_rooms_socketio[room_id]['messages'] = voice_rooms_socketio[room_id]['messages'][-20:]
        
        # Broadcast to room (except sender)
        await sio.emit('audio_message', message, room=room_id, skip_sid=sid)
        
        # Confirm to sender
        await sio.emit('audio_sent', {'message_id': message['id']}, room=sid)
        
    except Exception as e:
        print(f"Socket.IO: Error in send_audio: {e}")
        await sio.emit('error', {'message': str(e)}, room=sid)

@sio.event
async def ping_pong(sid, data):
    """Handle ping-pong for connection health"""
    await sio.emit('pong', {'timestamp': time.time()}, room=sid)

# Create ASGI application
socket_app = socketio.ASGIApp(sio, other_asgi_app=None)
