import threading
import json
import paho.mqtt.client as mqtt
from datetime import datetime
from pracownicy.models import Pracownik

class SimpleMQTTHandler:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.running = False
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("MQTT: Połączono z brokerem")
            client.subscribe("pracownicy/dodaj")
            client.subscribe("pracownicy/lista")
            client.subscribe("pracownicy/usun")
            client.subscribe("pracownicy/aktualizuj")
            print("MQTT: Nasłuchiwanie na 'pracownicy/dodaj', 'pracownicy/lista', 'pracownicy/usun' i 'pracownicy/aktualizuj'")
        else:
            print(f"MQTT: Błąd połączenia, kod: {rc}")
        
    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            print(f"MQTT: Otrzymano wiadomość z {topic}")
            
            if topic == "pracownicy/dodaj":
                self.dodaj_pracownika(payload)
            elif topic == "pracownicy/lista":
                self.wyslij_liste()
            elif topic == "pracownicy/usun":
                self.usun_pracownika(payload)
            elif topic == "pracownicy/aktualizuj":
                self.aktualizuj_pracownika(payload)
                
        except Exception as e:
            print(f"MQTT: Błąd: {e}")
            
    def dodaj_pracownika(self, payload):
        try:
            dane = json.loads(payload)
            
            # Sprawdź strukturę danych
            if 'data' in dane:
                dane = dane['data']
            
            # Mapowanie pól
            field_mapping = {
                'Imie': 'imie',
                'Nazwisko': 'nazwisko', 
                'Pesel': 'pesel',
                'DataZatrudnienia': 'data_zatrudnienia',
                'DataUrodzenia': 'data_urodzenia'
            }
            
            # Konwertuj nazwy pól
            normalized_data = {}
            for key, value in dane.items():
                if key in field_mapping:
                    normalized_data[field_mapping[key]] = value
                else:
                    normalized_data[key] = value
            
            # Sprawdź wymagane pola
            wymagane = ['imie', 'nazwisko', 'pesel', 'data_zatrudnienia', 'data_urodzenia']
            for pole in wymagane:
                if pole not in normalized_data:
                    raise ValueError(f"Brak pola: {pole}")

            # Konwertuj PESEL na string
            if isinstance(normalized_data['pesel'], int):
                normalized_data['pesel'] = str(normalized_data['pesel'])

            data_zatrudnienia = datetime.strptime(normalized_data['data_zatrudnienia'], '%Y-%m-%d').date()
            data_urodzenia = datetime.strptime(normalized_data['data_urodzenia'], '%Y-%m-%d').date()
            
            # Sprawdź duplikat
            if Pracownik.objects.filter(pesel=normalized_data['pesel']).exists():
                response = {"status": "error", "message": f"PESEL {normalized_data['pesel']} już istnieje"}
                self.client.publish("pracownicy/response", json.dumps(response))
                print(f"MQTT: Duplikat PESEL {normalized_data['pesel']}")
                return
            
            # Dodaj
            pracownik = Pracownik.objects.create(
                imie=normalized_data['imie'],
                nazwisko=normalized_data['nazwisko'],
                pesel=normalized_data['pesel'],
                data_zatrudnienia=data_zatrudnienia,
                data_urodzenia=data_urodzenia
            )
            
            response = {
                "status": "success", 
                "message": f"Dodano: {pracownik.imie} {pracownik.nazwisko}",
                "id": pracownik.id
            }
            self.client.publish("pracownicy/response", json.dumps(response))
            print(f"MQTT: Dodano pracownika {pracownik.imie} {pracownik.nazwisko}")
            
        except Exception as e:
            response = {"status": "error", "message": str(e)}
            self.client.publish("pracownicy/response", json.dumps(response))
            print(f"MQTT: Błąd dodawania: {e}")
            
    def wyslij_liste(self):
        try:
            pracownicy = Pracownik.objects.all()
            lista = []
            
            for p in pracownicy:
                lista.append({
                    'id': p.id,
                    'imie': p.imie,
                    'nazwisko': p.nazwisko,
                    'pesel': p.pesel,
                    'data_zatrudnienia': p.data_zatrudnienia.strftime('%Y-%m-%d'),
                    'data_urodzenia': p.data_urodzenia.strftime('%Y-%m-%d'),
                    'data_utworzenia': p.data_utworzenia.strftime('%Y-%m-%d %H:%M:%S'),
                    'data_modyfikacji': p.data_modyfikacji.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            response = {"status": "success", "count": len(lista), "pracownicy": lista}
            self.client.publish("pracownicy/lista_response", json.dumps(response))
            print(f"MQTT: Wysłano listę {len(lista)} pracowników")
            
        except Exception as e:
            response = {"status": "error", "message": str(e)}
            self.client.publish("pracownicy/lista_response", json.dumps(response))
            print(f"MQTT: Błąd listy: {e}")
            
    def usun_pracownika(self, payload):
        try:
            dane = json.loads(payload)
            
            # Sprawdź PESEL
            if 'pesel' not in dane:
                response = {"status": "error", "message": "Wymagane pole: 'pesel'"}
                self.client.publish("pracownicy/response", json.dumps(response))
                print("MQTT: Brak PESEL do usunięcia")
                return
            
            # Znajdź pracownika
            pracownik = Pracownik.objects.filter(pesel=dane['pesel']).first()
            if not pracownik:
                response = {"status": "error", "message": f"Pracownik z PESEL {dane['pesel']} nie istnieje"}
                self.client.publish("pracownicy/response", json.dumps(response))
                print(f"MQTT: Brak pracownika z PESEL {dane['pesel']}")
                return
            
            # Zapisz dane
            imie = pracownik.imie
            nazwisko = pracownik.nazwisko
            pracownik_id = pracownik.id
            
            # Usuń
            pracownik.delete()
            
            response = {
                "status": "success", 
                "message": f"Usunięto pracownika: {imie} {nazwisko}",
                "id": pracownik_id
            }
            self.client.publish("pracownicy/response", json.dumps(response))
            print(f"MQTT: Usunięto pracownika {imie} {nazwisko} (ID: {pracownik_id})")
            
        except json.JSONDecodeError:
            response = {"status": "error", "message": "Nieprawidłowy format JSON"}
            self.client.publish("pracownicy/response", json.dumps(response))
            print("MQTT: Nieprawidłowy JSON przy usuwaniu")
            
        except Exception as e:
            response = {"status": "error", "message": f"Błąd podczas usuwania: {str(e)}"}
            self.client.publish("pracownicy/response", json.dumps(response))
            print(f"MQTT: Błąd usuwania: {e}")
            
    def aktualizuj_pracownika(self, payload):
        try:
            dane = json.loads(payload)
            
            # Sprawdź PESEL
            if 'pesel' not in dane:
                response = {"status": "error", "message": "Wymagane pole: 'pesel'"}
                self.client.publish("pracownicy/response", json.dumps(response))
                print("MQTT: Brak PESEL do aktualizacji")
                return
            
            # Sprawdź dane do aktualizacji
            if 'to_update' not in dane:
                response = {"status": "error", "message": "Wymagane pole: 'to_update'"}
                self.client.publish("pracownicy/response", json.dumps(response))
                print("MQTT: Brak danych do aktualizacji")
                return
            
            # Znajdź pracownika
            pracownik = Pracownik.objects.filter(pesel=dane['pesel']).first()
            if not pracownik:
                response = {"status": "error", "message": f"Pracownik z PESEL {dane['pesel']} nie istnieje"}
                self.client.publish("pracownicy/response", json.dumps(response))
                print(f"MQTT: Brak pracownika z PESEL {dane['pesel']}")
                return
            
            # Zapisz stare dane
            stare_dane = f"{pracownik.imie} {pracownik.nazwisko}"
            to_update = dane['to_update']
            
            # Aktualizuj
            if 'Imie' in to_update:
                pracownik.imie = to_update['Imie']
            if 'Nazwisko' in to_update:
                pracownik.nazwisko = to_update['Nazwisko']
            if 'data_zatrudnienia' in to_update:
                pracownik.data_zatrudnienia = datetime.strptime(to_update['data_zatrudnienia'], '%Y-%m-%d').date()
            if 'data_urodzenia' in to_update:
                pracownik.data_urodzenia = datetime.strptime(to_update['data_urodzenia'], '%Y-%m-%d').date()
            
            pracownik.save()
            
            response = {
                "status": "success", 
                "message": f"Zaktualizowano pracownika: {stare_dane} → {pracownik.imie} {pracownik.nazwisko}",
                "id": pracownik.id
            }
            self.client.publish("pracownicy/response", json.dumps(response))
            print(f"MQTT: Zaktualizowano pracownika {stare_dane} → {pracownik.imie} {pracownik.nazwisko}")
            
        except json.JSONDecodeError:
            response = {"status": "error", "message": "Nieprawidłowy format JSON"}
            self.client.publish("pracownicy/response", json.dumps(response))
            print("MQTT: Nieprawidłowy JSON przy aktualizacji")
            
        except Exception as e:
            response = {"status": "error", "message": f"Błąd podczas aktualizacji: {str(e)}"}
            self.client.publish("pracownicy/response", json.dumps(response))
            print(f"MQTT: Błąd aktualizacji: {e}")
            
    def start_background(self):
        """Uruchamia MQTT w tle"""
        def run():
            try:
                self.client.connect("localhost", 1883, 60)
                self.running = True
                self.client.loop_forever()
            except Exception as e:
                print(f"MQTT: Nie można połączyć z brokerem: {e}")
                
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread

mqtt_handler = None

def start_mqtt():
    global mqtt_handler
    if mqtt_handler is None:
        mqtt_handler = SimpleMQTTHandler()
        mqtt_handler.start_background()
        print("MQTT Handler uruchomiony")
