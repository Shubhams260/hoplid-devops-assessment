import logging
import os
import time

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger("hoplid.database")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://hoplid:hoplid_local_only@localhost:5432/hoplid",
)

SLOW_QUERY_THRESHOLD_SECONDS = max(
    0.0, float(os.getenv("SLOW_QUERY_THRESHOLD_SECONDS", "0.5"))
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


@event.listens_for(engine, "before_cursor_execute")
def record_query_start(
    connection, cursor, statement, parameters, context, executemany
):
    context._hoplid_query_start = time.perf_counter()


@event.listens_for(engine, "after_cursor_execute")
def record_query_duration(
    connection, cursor, statement, parameters, context, executemany
):
    started = getattr(context, "_hoplid_query_start", None)
    if started is None:
        return

    duration = time.perf_counter() - started
    if duration >= SLOW_QUERY_THRESHOLD_SECONDS:
        operation = statement.lstrip().split(None, 1)[0].upper() if statement.strip() else "UNKNOWN"
        logger.warning(
            "slow_database_query operation=%s duration_seconds=%.3f threshold_seconds=%.3f",
            operation,
            duration,
            SLOW_QUERY_THRESHOLD_SECONDS,
        )


@event.listens_for(engine.pool, "checkout")
def log_pool_checkout(dbapi_connection, connection_record, connection_proxy):
    logger.debug("database_pool_connection_checked_out")


@event.listens_for(engine.pool, "checkin")
def log_pool_checkin(dbapi_connection, connection_record):
    logger.debug("database_pool_connection_checked_in")


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
