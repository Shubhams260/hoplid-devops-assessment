import os
import threading
import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError


def main():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit(
            "ERROR: Set DATABASE_URL explicitly to the dedicated hoplid_test database."
        )

    url = make_url(database_url)
    if url.database != "hoplid_test":
        raise SystemExit(
            f"SAFETY STOP: Expected database 'hoplid_test', got {url.database!r}."
        )

    engine = create_engine(
        database_url,
        pool_size=2,
        max_overflow=0,
        pool_timeout=1,
        pool_pre_ping=True,
    )

    first_connection_ready = threading.Event()
    release_first_connection = threading.Event()
    worker_errors = []

    def hold_first_connection():
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                first_connection_ready.set()
                if not release_first_connection.wait(timeout=10):
                    raise TimeoutError("Timed out waiting to release first connection.")
        except Exception as exc:
            worker_errors.append(exc)
            first_connection_ready.set()

    worker = threading.Thread(target=hold_first_connection, daemon=True)

    try:
        worker.start()

        if not first_connection_ready.wait(timeout=5):
            raise RuntimeError("First connection did not become ready.")

        if worker_errors:
            raise RuntimeError("First connection worker failed.") from worker_errors[0]

        with engine.connect() as second_connection:
            second_connection.execute(text("SELECT 1"))

            started = time.monotonic()
            try:
                with engine.connect() as _third_connection:
                    raise AssertionError(
                        "Expected the third connection to time out, but it succeeded."
                    )
            except SQLAlchemyTimeoutError:
                elapsed = time.monotonic() - started
                print(f"Database target: {url.database}")
                print("Pool size: 2")
                print("Max overflow: 0")
                print("Pool timeout: 1s")
                print(f"Observed pool timeout after {elapsed:.3f}s")
                print("PASS: Pool exhaustion was reproduced without writing data.")

    finally:
        release_first_connection.set()
        worker.join(timeout=5)
        engine.dispose()

        if worker.is_alive():
            raise RuntimeError("Connection-holding worker did not stop cleanly.")


if __name__ == "__main__":
    main()
