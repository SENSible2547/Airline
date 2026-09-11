import psycopg2
import psycopg2.extras

DB_CONFIG = dict(
    host="localhost",
    dbname="airline_reservations",
    user="postgres",
    password="postgres",
)


def get_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn
