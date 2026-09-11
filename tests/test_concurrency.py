"""
Prueba de concurrencia para NFR-02:
"Si dos pasajeros piden el ultimo asiento al mismo tiempo, el sistema debe
garantizar que solo uno complete el hold."

El vuelo AR101 (flight_id=3) tiene exactamente 1 asiento economy disponible
(ver db/seed.sql). Este script dispara 2 solicitudes POST /reservations
en paralelo, exactamente al mismo tiempo, y verifica:
  1. Exactamente una obtiene 201 (reserva creada).
  2. Exactamente una obtiene 409 (sin disponibilidad).
  3. El inventario final no queda sobrevendido (held+sold <= total).
"""

import threading
import requests
import psycopg2

URL = "http://localhost:8000/reservations"

payload_a = {
    "passenger": {"name": "Carlos Ruiz", "email": "carlos@test.com", "document_id": "CC900"},
    "segments": [{"flight_id": 3, "fare_class": "economy"}],
}
payload_b = {
    "passenger": {"name": "Maria Lopez", "email": "maria@test.com", "document_id": "CC901"},
    "segments": [{"flight_id": 3, "fare_class": "economy"}],
}

results = {}
barrier = threading.Barrier(2)  # fuerza a que ambos hilos disparen al mismo instante


def fire(name, payload):
    barrier.wait()  # ambos hilos esperan aqui y sueltan a la vez
    r = requests.post(URL, json=payload)
    results[name] = (r.status_code, r.json())


t1 = threading.Thread(target=fire, args=("request_A", payload_a))
t2 = threading.Thread(target=fire, args=("request_B", payload_b))

t1.start()
t2.start()
t1.join()
t2.join()

print("=== Resultado de las 2 solicitudes simultaneas ===")
for name, (status, body) in results.items():
    print(f"{name}: HTTP {status} -> {body}")

statuses = sorted(s for s, _ in results.values())
assert statuses == [201, 409], f"Se esperaba [201, 409], se obtuvo {statuses}"

conn = psycopg2.connect(host="localhost", dbname="airline_reservations", user="postgres", password="postgres")
cur = conn.cursor()
cur.execute("SELECT total_seats, held_seats, sold_seats FROM seat_inventory WHERE flight_id=3 AND fare_class='economy'")
total, held, sold = cur.fetchone()
print(f"\n=== Estado final del inventario (flight_id=3, economy) ===")
print(f"total_seats={total}  held_seats={held}  sold_seats={sold}")
assert held + sold <= total, "SOBREVENTA DETECTADA"
assert held + sold == 1, "El inventario deberia reflejar exactamente 1 asiento tomado"

print("\n>>> PRUEBA EXITOSA: no hubo sobreventa. El bloqueo pesimista (SELECT FOR UPDATE) funciono correctamente.")
