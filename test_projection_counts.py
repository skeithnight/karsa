import psycopg

conn = psycopg.connect("postgresql://karsa:karsa_password@localhost:5432/karsa_db")
with conn.cursor() as cur:
    for table in ["attribution_lineages", "attribution_lineage_nodes", "attribution_facts", "attribution_assessments"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"{table}: {cur.fetchone()[0]}")
