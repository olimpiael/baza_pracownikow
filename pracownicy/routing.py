from django.urls import path, re_path
from .consumers import PracownicyConsumer, VoiceRoomConsumer
from baza_pracownikow.pracownicy import consumers


websocket_urlpatterns = [
    path('ws/pracownicy/', PracownicyConsumer.as_asgi()),
    re_path(r'ws/room/(?P<room_name>\w+)/$', consumers.VoiceRoomConsumer.as_asgi())
]
