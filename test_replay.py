import psycopg

conn = psycopg.connect("postgresql://karsa:karsa_password@localhost:5432/karsa_db")
with conn.cursor() as cur:
    cur.execute("TRUNCATE TABLE attribution_lineages CASCADE")
    cur.execute("UPDATE projection_checkpoints SET last_processed_sequence = 0 WHERE projection_name = 'portfolio_read_models'")
    conn.commit()
