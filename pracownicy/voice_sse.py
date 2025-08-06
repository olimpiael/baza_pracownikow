import json
import time
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
import uuid

# Shared voice room data
voice_rooms_sse = {}

@login_required
def voice_room_stream(request, room_id):
    """
    Server-Sent Events stream dla voice room
    """
    user_id = str(request.user.id)
    
    def event_stream():
        # Initialize room
        if room_id not in voice_rooms_sse:
            voice_rooms_sse[room_id] = {
                'messages': [],
                'participants': set()
            }
        
        voice_rooms_sse[room_id]['participants'].add(user_id)
        
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connected', 'room_id': room_id, 'participants': len(voice_rooms_sse[room_id]['participants'])})}\n\n"
        
        last_message_count = 0
        
        while True:
            try:
                messages = voice_rooms_sse.get(room_id, {}).get('messages', [])
                
                # Send new messages
                if len(messages) > last_message_count:
                    new_messages = messages[last_message_count:]
                    # Filter out own messages
                    other_messages = [msg for msg in new_messages if msg['user_id'] != user_id]
                    
                    for message in other_messages:
                        yield f"data: {json.dumps(message)}\n\n"
                    
                    last_message_count = len(messages)
                
                # Send heartbeat every 10 seconds
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"
                
                time.sleep(2)  # Check every 2 seconds
                
            except GeneratorExit:
                # Client disconnected
                if room_id in voice_rooms_sse:
                    voice_rooms_sse[room_id]['participants'].discard(user_id)
                break
            except Exception as e:
                print(f"SSE Error: {e}")
                break
    
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = 'Cache-Control'
    
    return response

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def send_voice_sse(request):
    """
    Wyślij audio chunk przez SSE
    """
    try:
        data = json.loads(request.body)
        room_id = data.get('room_id')
        audio_chunk = data.get('audio_chunk')
        user_id = str(request.user.id)
        
        if not room_id or not audio_chunk:
            return JsonResponse({'error': 'Missing data'}, status=400)
        
        # Initialize room
        if room_id not in voice_rooms_sse:
            voice_rooms_sse[room_id] = {
                'messages': [],
                'participants': set()
            }
        
        # Add message
        message = {
            'id': str(uuid.uuid4()),
            'type': 'audio',
            'user_id': user_id,
            'username': request.user.username,
            'audio_chunk': audio_chunk,
            'timestamp': time.time()
        }
        
        voice_rooms_sse[room_id]['messages'].append(message)
        
        # Keep only last 30 messages
        if len(voice_rooms_sse[room_id]['messages']) > 30:
            voice_rooms_sse[room_id]['messages'] = voice_rooms_sse[room_id]['messages'][-30:]
        
        return JsonResponse({'status': 'sent', 'message_id': message['id']})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
