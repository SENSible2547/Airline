from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from app.db import get_connection

app = FastAPI(title="Airline Reservation System - MVP")


# ---------- Schemas ----------

class PassengerIn(BaseModel):
    name: str
    email: str
    document_id: str


class SegmentIn(BaseModel):
    flight_id: int
    fare_class: str  # 'economy' | 'business'


class ReservationIn(BaseModel):
    passenger: PassengerIn
    segments: List[SegmentIn]


# ---------- 1. Buscar vuelos disponibles (FR-01) ----------

@app.get("/flights/search")
def search_flights(origin: str, destination: str, date: str):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT f.id, f.flight_number, f.flight_date, f.departure_time, f.arrival_time,
                   fa.fare_class, fa.price,
                   (si.total_seats - si.held_seats - si.sold_seats) AS seats_available
            FROM flights f
            JOIN routes r ON f.route_id = r.id
            JOIN fares fa ON fa.flight_id = f.id
            JOIN seat_inventory si ON si.flight_id = f.id AND si.fare_class = fa.fare_class
            WHERE r.origin_code = %s AND r.destination_code = %s AND f.flight_date = %s
            ORDER BY f.departure_time, fa.fare_class
            """,
            (origin.upper(), destination.upper(), date),
        )
        rows = cur.fetchall()
        results = {}
        for r in rows:
            fid = r[0]
            if fid not in results:
                results[fid] = {
                    "flight_id": fid,
                    "flight_number": r[1],
                    "date": str(r[2]),
                    "departure_time": str(r[3]),
                    "arrival_time": str(r[4]),
                    "fares": [],
                }
            results[fid]["fares"].append(
                {"fare_class": r[5], "price": float(r[6]), "seats_available": r[7]}
            )
        return list(results.values())
    finally:
        conn.close()


# ---------- 2. Crear reserva (FR-02/FR-03/FR-04) con bloqueo pesimista (NFR-02) ----------

@app.post("/reservations", status_code=201)
def create_reservation(payload: ReservationIn):
    if not payload.segments:
        raise HTTPException(400, "La reserva debe tener al menos un segmento de vuelo")

    conn = get_connection()
    conn.autocommit = False
    try:
        cur = conn.cursor()

        # Bloquear las filas de seat_inventory en un orden determinista
        # (flight_id, fare_class) para evitar deadlocks si hay varios segmentos.
        ordered_segments = sorted(payload.segments, key=lambda s: (s.flight_id, s.fare_class))

        locked_rows = {}
        for seg in ordered_segments:
            cur.execute(
                """
                SELECT id, total_seats, held_seats, sold_seats
                FROM seat_inventory
                WHERE flight_id = %s AND fare_class = %s
                FOR UPDATE
                """,
                (seg.flight_id, seg.fare_class),
            )
            row = cur.fetchone()
            if row is None:
                conn.rollback()
                raise HTTPException(404, f"No existe inventario para flight_id={seg.flight_id}, clase={seg.fare_class}")

            inv_id, total, held, sold = row
            if held + sold >= total:
                conn.rollback()
                raise HTTPException(409, f"Sin disponibilidad: flight_id={seg.flight_id}, clase={seg.fare_class}")

            locked_rows[(seg.flight_id, seg.fare_class)] = inv_id

        # Pasajero (upsert simple por document_id)
        cur.execute("SELECT id FROM passengers WHERE document_id = %s", (payload.passenger.document_id,))
        p = cur.fetchone()
        if p:
            passenger_id = p[0]
        else:
            cur.execute(
                "INSERT INTO passengers (name, email, document_id) VALUES (%s,%s,%s) RETURNING id",
                (payload.passenger.name, payload.passenger.email, payload.passenger.document_id),
            )
            passenger_id = cur.fetchone()[0]

        hold_expires_at = datetime.utcnow() + timedelta(minutes=15)
        cur.execute(
            "INSERT INTO reservations (passenger_id, status, hold_expires_at) VALUES (%s,'hold',%s) RETURNING id",
            (passenger_id, hold_expires_at),
        )
        reservation_id = cur.fetchone()[0]

        for seg in ordered_segments:
            cur.execute(
                "SELECT id FROM fares WHERE flight_id=%s AND fare_class=%s",
                (seg.flight_id, seg.fare_class),
            )
            fare_id = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO reservation_segments (reservation_id, flight_id, fare_id, fare_class) VALUES (%s,%s,%s,%s)",
                (reservation_id, seg.flight_id, fare_id, seg.fare_class),
            )

            inv_id = locked_rows[(seg.flight_id, seg.fare_class)]
            cur.execute(
                "UPDATE seat_inventory SET held_seats = held_seats + 1 WHERE id = %s",
                (inv_id,),
            )

        conn.commit()
        return {
            "reservation_id": reservation_id,
            "status": "hold",
            "hold_expires_at": hold_expires_at.isoformat(),
            "segments": [s.dict() for s in ordered_segments],
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        conn.close()


# ---------- 3. Consultar reserva existente (FR-05) ----------

@app.get("/reservations/{reservation_id}")
def get_reservation(reservation_id: int):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT r.id, r.status, r.hold_expires_at, r.created_at,
                   p.name, p.email, p.document_id
            FROM reservations r
            JOIN passengers p ON p.id = r.passenger_id
            WHERE r.id = %s
            """,
            (reservation_id,),
        )
        res = cur.fetchone()
        if res is None:
            raise HTTPException(404, "Reserva no encontrada")

        cur.execute(
            """
            SELECT rs.flight_id, f.flight_number, f.flight_date, rs.fare_class
            FROM reservation_segments rs
            JOIN flights f ON f.id = rs.flight_id
            WHERE rs.reservation_id = %s
            """,
            (reservation_id,),
        )
        segments = cur.fetchall()

        return {
            "reservation_id": res[0],
            "status": res[1],
            "hold_expires_at": res[2].isoformat() if res[2] else None,
            "created_at": res[3].isoformat(),
            "passenger": {"name": res[4], "email": res[5], "document_id": res[6]},
            "segments": [
                {"flight_id": s[0], "flight_number": s[1], "date": str(s[2]), "fare_class": s[3]}
                for s in segments
            ],
        }
    finally:
        conn.close()
