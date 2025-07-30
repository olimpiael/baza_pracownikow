from .models import Pracownik, Zespol
from rest_framework import serializers

class ZespolSerializer(serializers.ModelSerializer):
    liczba_pracownikow = serializers.ReadOnlyField()
    lider_nazwa = serializers.CharField(source='lider.__str__', read_only=True)
    
    class Meta:
        model = Zespol
        fields = ['id', 'nazwa', 'opis', 'lider', 'lider_nazwa', 'liczba_pracownikow', 'data_utworzenia', 'data_modyfikacji']

class PracownikSerializer(serializers.ModelSerializer):
    zespol_nazwa = serializers.CharField(source='zespol.nazwa', read_only=True)
    
    class Meta:
        model = Pracownik
        fields = ['id', 'imie', 'nazwisko', 'pesel', 
        'stanowisko', 'zespol', 'zespol_nazwa', 'data_zatrudnienia', 'data_urodzenia', 'data_utworzenia', 'data_modyfikacji']

class CVUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pracownik
        fields = ['cv']

from .models import VoiceRoom

class VoiceRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceRoom
        fields = "__all__"