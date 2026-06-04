from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# PostgreSQL istenmişti ancak 1 günde ayağa kaldırmak için en hızlısı yerel SQLite'tır.
# Mimari aynı kalır, sadece buradaki URL ileride PostgreSQL URL'si ile değiştirilir.
SQLALCHEMY_DATABASE_URL = "sqlite:///./coddest.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()