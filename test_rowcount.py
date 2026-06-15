import sqlalchemy as sa
from sqlalchemy.orm import Session

engine = sa.create_engine('postgresql://postgres:postgres@localhost:5433/postgres')
with Session(engine) as session:
    session.execute(sa.text("DROP TABLE IF EXISTS regime_sessions CASCADE"))
    session.execute(sa.text("""
        CREATE TABLE regime_sessions (
            session_urn VARCHAR PRIMARY KEY,
            state VARCHAR NOT NULL,
            aggregate_version INTEGER NOT NULL
        )
    """))
    
    insert_stmt = sa.text("""
        INSERT INTO regime_sessions (session_urn, state, aggregate_version) 
        VALUES (:urn, :state, :ver)
    """)
    session.execute(insert_stmt, {"urn": "urn:sess1", "state": "INITIATED", "ver": 1})
    
    update_stmt = sa.text("""
        UPDATE regime_sessions 
        SET state = :state, aggregate_version = :ver 
        WHERE session_urn = :urn AND aggregate_version = :curr_ver
    """)
    res = session.execute(update_stmt, {
        "state": "ANALYZING", 
        "ver": 2, 
        "urn": "urn:sess1",
        "curr_ver": 1
    })
    print(f"Rowcount: {res.rowcount}")
