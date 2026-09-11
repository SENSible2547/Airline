INSERT INTO airports (code, city, country) VALUES
  ('BOG', 'Bogota', 'Colombia'),
  ('MDE', 'Medellin', 'Colombia'),
  ('MIA', 'Miami', 'USA');

INSERT INTO routes (origin_code, destination_code) VALUES
  ('BOG', 'MDE'),   -- route 1
  ('BOG', 'MIA');   -- route 2

-- Vuelo normal, con varios asientos (para probar busqueda)
INSERT INTO flights (route_id, flight_number, flight_date, departure_time, arrival_time, status) VALUES
  (1, 'AR100', '2026-10-15', '08:00', '09:00', 'scheduled'),
  (2, 'AR200', '2026-10-15', '10:00', '14:00', 'scheduled');

-- Vuelo critico: solo queda 1 asiento economy -> escenario de la prueba de concurrencia
INSERT INTO flights (route_id, flight_number, flight_date, departure_time, arrival_time, status) VALUES
  (1, 'AR101', '2026-10-16', '09:00', '10:00', 'scheduled');

INSERT INTO fares (flight_id, fare_class, price) VALUES
  (1, 'economy', 250000), (1, 'business', 600000),
  (2, 'economy', 1200000), (2, 'business', 3500000),
  (3, 'economy', 260000);

INSERT INTO seat_inventory (flight_id, fare_class, total_seats, held_seats, sold_seats) VALUES
  (1, 'economy', 120, 0, 0), (1, 'business', 20, 0, 0),
  (2, 'economy', 180, 0, 0), (2, 'business', 30, 0, 0),
  (3, 'economy', 1, 0, 0);   -- <-- ultimo asiento, para la prueba de concurrencia
