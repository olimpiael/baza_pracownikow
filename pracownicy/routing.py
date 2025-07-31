from django.urls import path, re_path
from .consumers import PracownicyConsumer, VoiceRoomConsumer

websocket_urlpatterns = [
    path('ws/pracownicy/', PracownicyConsumer.as_asgi()),
    re_path(r'^ws/room/(?P<room_name>[^/]+)/$', VoiceRoomConsumer.as_asgi()),
]
