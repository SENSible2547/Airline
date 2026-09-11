# Airline Reservation System — MVP backend (seccion 5.6)

Implementacion parcial y funcional del backend disenado en 5.4, sobre la base
de datos modelada en 5.3. El objetivo no es el sistema completo, sino validar
que las decisiones de diseno (bloqueo pesimista, multi-tramo, hold temporal)
son implementables y funcionan bajo concurrencia real.

## Alcance minimo cubierto

- `GET /flights/search` — busqueda de vuelos disponibles (FR-01)
- `POST /reservations` — crear una reserva (hold), multi-tramo, con bloqueo
  pesimista sobre el inventario de asientos (FR-02/FR-03/FR-04, NFR-02)
- `GET /reservations/{id}` — consultar una reserva existente (FR-05)

## Como ejecutarlo

Requisitos: PostgreSQL 16, Python 3.11+

```bash
# 1. Crear la base de datos
sudo -u postgres psql -c "CREATE DATABASE airline_reservations;"
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"

# 2. Cargar el esquema y los datos de prueba
sudo -u postgres psql -d airline_reservations -f db/schema.sql
sudo -u postgres psql -d airline_reservations -f db/seed.sql

# 3. Instalar dependencias y levantar la API
pip install -r requirements.txt
uvicorn app.main:app --reload

# 4. Probar
curl "http://localhost:8000/flights/search?origin=BOG&destination=MDE&date=2026-10-15"
```

## Prueba de concurrencia (evidencia para NFR-02)

`tests/test_concurrency.py` dispara 2 solicitudes `POST /reservations` en
paralelo (con un `threading.Barrier` para forzar que salgan en el mismo
instante) contra el vuelo `AR101` (flight_id=3), que en `seed.sql` tiene
**exactamente 1 asiento economy disponible**.

```bash
python3 tests/test_concurrency.py
```

### Resultado de 3 corridas reales (ejecutadas durante el desarrollo)

```
--- Corrida 1 ---
request_B: HTTP 201 -> reservation_id 1 creada
request_A: HTTP 409 -> Sin disponibilidad
Inventario final: total_seats=1 held_seats=1 sold_seats=0
>>> PRUEBA EXITOSA: no hubo sobreventa.

--- Corrida 2 ---
request_A: HTTP 409 -> Sin disponibilidad
request_B: HTTP 201 -> reservation_id 2 creada
Inventario final: total_seats=1 held_seats=1 sold_seats=0
>>> PRUEBA EXITOSA: no hubo sobreventa.

--- Corrida 3 ---
request_A: HTTP 201 -> reservation_id 3 creada
request_B: HTTP 409 -> Sin disponibilidad
Inventario final: total_seats=1 held_seats=1 sold_seats=0
>>> PRUEBA EXITOSA: no hubo sobreventa.
```

El ganador de la carrera cambia entre corridas (no hay un sesgo de orden en
el codigo), lo que confirma que la seguridad viene del `SELECT ... FOR
UPDATE` sobre la fila de `seat_inventory` dentro de la transaccion, y no de
un accidente de temporizacion. En ningun caso `held_seats + sold_seats`
supero `total_seats`.

## Desviaciones respecto al diseno de 5.3 / 5.4 (declaradas explicitamente)

| Decision en 5.3/5.4 | Que se implemento en el MVP | Motivo |
|---|---|---|
| `ScheduledFlight` distinto de `Flight` (plantilla vs instancia) | Se fusionaron en una sola tabla `flights` | Para el MVP no hace falta generar instancias recurrentes; se documenta como simplificacion, no como cambio de decision definitivo. Al implementar el sistema completo, se separan de nuevo. |
| Entidades `Aircraft`, `Seat` (asiento fisico), `Payment`, `Agency`, `ReservationStatusHistory` | No implementadas en este MVP | Fuera del alcance minimo pedido en 5.6 (buscar, reservar, consultar). El check-in, el pago y el historial de auditoria se dejan para la implementacion completa. |
| Conexion a la base de datos | `psycopg2` sincrono en vez de un driver async | Simplifica la demostracion del `FOR UPDATE`; en produccion se evaluaria `asyncpg` para mejor throughput, sin cambiar el mecanismo de bloqueo. |
| Mecanismo de concurrencia | Igual al diseñado: `SELECT ... FOR UPDATE` por fila `(flight_id, fare_class)` | Sin cambios — validado con la prueba anterior. |

## Estructura del proyecto

```
airline-backend/
├── app/
│   ├── main.py       # endpoints FastAPI
│   └── db.py         # conexion a PostgreSQL
├── db/
│   ├── schema.sql    # esquema (ver tabla de desviaciones arriba)
│   └── seed.sql       # datos de prueba, incluye el vuelo de 1 asiento
├── tests/
│   └── test_concurrency.py
└── requirements.txt
```
