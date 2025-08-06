import json
import base64
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.core.cache import cache
import time
import uuid
from django.contrib.auth.decorators import login_required

# Temporary storage for voice messages (use Redis in production)
voice_rooms = {}

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def send_voice_chunk(request):
    """
    Przyjmuje chunk audio i zapisuje do pamięci
    """
    try:
        data = json.loads(request.body)
        room_id = data.get('room_id')
        audio_chunk = data.get('audio_chunk')  # base64 encoded
        user_id = str(request.user.id)
        
        if not room_id or not audio_chunk:
            return JsonResponse({'error': 'Missing room_id or audio_chunk'}, status=400)
        
        # Create room if doesn't exist
        if room_id not in voice_rooms:
            voice_rooms[room_id] = {
                'messages': [],
                'participants': set()
            }
        
        # Add participant
        voice_rooms[room_id]['participants'].add(user_id)
        
        # Store audio chunk with timestamp
        message = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'username': request.user.username,
            'audio_chunk': audio_chunk,
            'timestamp': time.time(),
            'type': 'audio'
        }
        
        voice_rooms[room_id]['messages'].append(message)
        
        # Keep only last 50 messages per room
        if len(voice_rooms[room_id]['messages']) > 50:
            voice_rooms[room_id]['messages'] = voice_rooms[room_id]['messages'][-50:]
        
        return JsonResponse({
            'status': 'success',
            'message_id': message['id'],
            'participants': len(voice_rooms[room_id]['participants'])
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
@login_required
def get_voice_messages(request, room_id):
    """
    Long polling - czeka na nowe wiadomości audio
    """
    user_id = str(request.user.id)
    last_message_id = request.GET.get('last_message_id')
    timeout = 30  # 30 sekund timeout
    start_time = time.time()
    
    # Add user to room participants
    if room_id not in voice_rooms:
        voice_rooms[room_id] = {
            'messages': [],
            'participants': set()
        }
    
    voice_rooms[room_id]['participants'].add(user_id)
    
    while time.time() - start_time < timeout:
        # Get messages after last_message_id
        messages = voice_rooms.get(room_id, {}).get('messages', [])
        
        if last_message_id:
            # Find messages after last_message_id
            new_messages = []
            found_last = False
            for msg in messages:
                if found_last and msg['user_id'] != user_id:  # Don't send back own messages
                    new_messages.append(msg)
                elif msg['id'] == last_message_id:
                    found_last = True
        else:
            # First request - send recent messages from others
            new_messages = [msg for msg in messages[-10:] if msg['user_id'] != user_id]
        
        if new_messages:
            return JsonResponse({
                'messages': new_messages,
                'participants': len(voice_rooms[room_id]['participants'])
            })
        
        time.sleep(0.5)  # Check every 500ms
    
    # Timeout - return empty
    return JsonResponse({
        'messages': [],
        'participants': len(voice_rooms.get(room_id, {}).get('participants', []))
    })

@require_http_methods(["POST"])
@login_required
def join_voice_room(request, room_id):
    """
    Dołącz do pokoju głosowego
    """
    user_id = str(request.user.id)
    
    if room_id not in voice_rooms:
        voice_rooms[room_id] = {
            'messages': [],
            'participants': set()
        }
    
    voice_rooms[room_id]['participants'].add(user_id)
    
    return JsonResponse({
        'status': 'joined',
        'room_id': room_id,
        'participants': len(voice_rooms[room_id]['participants'])
    })

@require_http_methods(["POST"])
@login_required
def leave_voice_room(request, room_id):
    """
    Opuść pokój głosowy
    """
    user_id = str(request.user.id)
    
    if room_id in voice_rooms:
        voice_rooms[room_id]['participants'].discard(user_id)
        
        # Clean up empty rooms
        if not voice_rooms[room_id]['participants']:
            voice_rooms[room_id]['messages'] = []
    
    return JsonResponse({
        'status': 'left',
        'room_id': room_id
    })
