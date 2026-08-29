from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.core.config import settings

db_url = settings.db_url
is_sqlite = db_url.startswith("sqlite")

connect_args = {}
if is_sqlite:
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def run_migrations():
    from sqlalchemy import inspect, text
    
    # Import Base here to avoid circular imports
    from backend.app.models.models import Base
    Base.metadata.create_all(bind=engine)
    
    inspector = inspect(engine)
    tables_to_migrate = ["customers", "transactions", "recovery_cases", "audit_logs", "webhook_events", "policy_configs"]
    
    with engine.connect() as conn:
        for table in tables_to_migrate:
            if not inspector.has_table(table):
                continue
            columns = [col["name"] for col in inspector.get_columns(table)]
            if "merchant_id" not in columns:
                print(f"Altering table {table} to add merchant_id column.")
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN merchant_id TEXT;"))
                conn.commit()
            if table == "transactions" and "is_demo" not in columns:
                print("Altering table transactions to add is_demo column.")
                conn.execute(text("ALTER TABLE transactions ADD COLUMN is_demo BOOLEAN DEFAULT 0;"))
                conn.commit()
            if table == "recovery_cases" and "explanation" not in columns:
                print("Altering table recovery_cases to add explanation column.")
                conn.execute(text("ALTER TABLE recovery_cases ADD COLUMN explanation TEXT;"))
                conn.commit()

