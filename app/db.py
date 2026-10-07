from collections.abc import Generator

from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db(database_engine: Engine) -> None:
    from app.models import Tariff

    Base.metadata.create_all(database_engine)
    tariffs = [
        {"title": "basic", "price": 990000},
        {"title": "standard", "price": 1990000},
        {"title": "premium", "price": 2990000},
    ]
    with Session(database_engine) as session:
        for tariff in tariffs:
            exists = session.scalar(select(Tariff).where(Tariff.title == tariff["title"]))
            if exists is None:
                session.add(Tariff(**tariff))
        session.commit()
