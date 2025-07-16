import os
import psycopg2
from psycopg2 import sql


def run_migrations():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()

    # Create migrations table if not exists
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS _migrations (
            version VARCHAR(50) PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT NOW()
        )
    """
    )

    # Get applied migrations
    cur.execute("SELECT version FROM _migrations ORDER BY version")
    applied = {row[0] for row in cur.fetchall()}

    # Apply new migrations
    migration_files = sorted(os.listdir("db/migrations"))
    for filename in migration_files:
        if filename.endswith(".sql") and filename not in applied:
            try:
                with open(f"db/migrations/{filename}") as f:
                    migration_sql = f.read()
                
                # Execute migration in a transaction
                cur.execute(migration_sql)
                
                # Use parameterized query to insert migration record
                cur.execute(
                    "INSERT INTO _migrations (version) VALUES (%s)", 
                    (filename,)
                )
                print(f"Applied migration: {filename}")
            except Exception as e:
                print(f"Failed to apply migration {filename}: {e}")
                conn.rollback()
                raise

    conn.commit()
    conn.close()


#
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# from sqlalchemy.ext.declarative import declarative_base
#
#
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
#
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#
# Base = declarative_base()
#
#
# def init_db():
#     Base.metadata.create_all(bind=engine)
