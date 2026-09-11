import psycopg2
import psycopg2.extras

DB_CONFIG = dict(
    host="database-3.cqyakzg5wwqq.us-east-1.rds.amazonaws.com",  # el endpoint de tu instancia RDS
    dbname="airline_reservations",
    user="postgres",
    password="o4oh1647t",
)

def get_connection():
    conn = psycopg2.connect(host="database-3.cqyakzg5wwqq.us-east-1.rds.amazonaws.com", dbname="airline_reservations",
        user="postgres",
        password="o4oh1647t")
    return conn


