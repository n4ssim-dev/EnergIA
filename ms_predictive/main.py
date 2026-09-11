from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from routes.ingest import router as ingest_router, get_target_connection
from routes.diagnostics import router as diagnostics_router

app = FastAPI()
app.include_router(router=ingest_router)
app.include_router(router=diagnostics_router)

@app.get("/health")
def health():
    conn = get_target_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            )
            tables = [row[0] for row in cur.fetchall()]

            rows_par_table = {}
            for table in tables:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                rows_par_table[table] = cur.fetchone()[0]
    finally:
        conn.close()

    return {
        "status": "healthy",
        "nombre_tables": len(tables),
        "rows_par_table": rows_par_table,
    }
