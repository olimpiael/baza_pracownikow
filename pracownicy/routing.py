from django.urls import path, re_path
from .consumers import PracownicyConsumer, VoiceRoomConsumer
from .simple_consumer import SimpleVoiceRoomConsumer

websocket_urlpatterns = [
    path('ws/pracownicy/', PracownicyConsumer.as_asgi()),
    # Use simple consumer for testing WebSocket connectivity
    re_path(r'^ws/room/(?P<room_name>[^/]+)/$', SimpleVoiceRoomConsumer.as_asgi()),
    # Original complex consumer (commented for now)
    # re_path(r'^ws/room/(?P<room_name>[^/]+)/$', VoiceRoomConsumer.as_asgi()),
]
