import psycopg2
try:
    conn = psycopg2.connect(dbname="postgres", host="localhost", port=5432)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print(cur.fetchone()[0])
    try:
        cur.execute("CREATE DATABASE karsa_test_db;")
    except Exception as e:
        print("DB exists or error:", e)
    conn.close()
    print("Success")
except Exception as e:
    print("Error without password:", e)

try:
    conn = psycopg2.connect(dbname="postgres", user="dwiki.nugraha", host="localhost", port=5432)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print("Success with dwiki.nugraha")
except Exception as e:
    pass

