-- Esquema transaccional MVP para el sistema de reservas de vuelos
-- Basado en el modelo entidad-relacion de la seccion 5.3, con simplificaciones
-- documentadas en el README (seccion "Desviaciones respecto a 5.3/5.4").

CREATE TABLE airports (
    code        CHAR(3) PRIMARY KEY,
    city        VARCHAR(80) NOT NULL,
    country     VARCHAR(80) NOT NULL
);

CREATE TABLE routes (
    id                  SERIAL PRIMARY KEY,
    origin_code         CHAR(3) NOT NULL REFERENCES airports(code),
    destination_code    CHAR(3) NOT NULL REFERENCES airports(code),
    CHECK (origin_code <> destination_code)
);

-- Simplificacion MVP: se fusionaron ScheduledFlight y Flight en una sola tabla.
-- Cada fila ya es una instancia concreta (vuelo + fecha), no una plantilla recurrente.
CREATE TABLE flights (
    id              SERIAL PRIMARY KEY,
    route_id        INTEGER NOT NULL REFERENCES routes(id),
    flight_number   VARCHAR(10) NOT NULL,
    flight_date     DATE NOT NULL,
    departure_time  TIME NOT NULL,
    arrival_time    TIME NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'scheduled'
);

CREATE TABLE fares (
    id              SERIAL PRIMARY KEY,
    flight_id       INTEGER NOT NULL REFERENCES flights(id),
    fare_class      VARCHAR(20) NOT NULL CHECK (fare_class IN ('economy','business')),
    price           NUMERIC(10,2) NOT NULL,
    UNIQUE (flight_id, fare_class)
);

-- Aqui vive el control de sobreventa (decision central de 5.3/5.4).
-- held = reservas en estado "hold" sin confirmar todavia
-- sold = reservas confirmadas
-- La fila (flight_id, fare_class) es la unidad de bloqueo pesimista.
CREATE TABLE seat_inventory (
    id              SERIAL PRIMARY KEY,
    flight_id       INTEGER NOT NULL REFERENCES flights(id),
    fare_class      VARCHAR(20) NOT NULL CHECK (fare_class IN ('economy','business')),
    total_seats     INTEGER NOT NULL,
    held_seats      INTEGER NOT NULL DEFAULT 0,
    sold_seats      INTEGER NOT NULL DEFAULT 0,
    UNIQUE (flight_id, fare_class),
    CHECK (held_seats + sold_seats <= total_seats)
);

CREATE TABLE passengers (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(120) NOT NULL,
    email           VARCHAR(120) NOT NULL,
    document_id     VARCHAR(40) NOT NULL
);

CREATE TABLE reservations (
    id                  SERIAL PRIMARY KEY,
    passenger_id        INTEGER NOT NULL REFERENCES passengers(id),
    status              VARCHAR(20) NOT NULL DEFAULT 'hold',  -- hold | confirmed | cancelled | expired
    hold_expires_at     TIMESTAMP,
    created_at          TIMESTAMP NOT NULL DEFAULT now()
);

-- Resuelve el itinerario multi-tramo: una reserva -> muchos segmentos.
CREATE TABLE reservation_segments (
    id              SERIAL PRIMARY KEY,
    reservation_id  INTEGER NOT NULL REFERENCES reservations(id),
    flight_id       INTEGER NOT NULL REFERENCES flights(id),
    fare_id         INTEGER NOT NULL REFERENCES fares(id),
    fare_class      VARCHAR(20) NOT NULL
);
