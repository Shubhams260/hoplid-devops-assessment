import os
from concurrent.futures import ThreadPoolExecutor

import httpx
import psycopg
import pytest

API_URL = os.getenv("API_URL", "http://localhost:8001")
DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://hoplid:hoplid_local_only@localhost:5432/hoplid_test",
)

@pytest.fixture(scope="module")
def db():
    if "hoplid_test" not in DATABASE_URL:
        pytest.fail(
            "Safety guard: integration tests must use the hoplid_test database. "
            "Set TEST_DATABASE_URL to the dedicated test database."
        )

    conn = psycopg.connect(DATABASE_URL)
    conn = psycopg.connect(DATABASE_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id UUID PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                vendor_id VARCHAR(100) NOT NULL,
                items JSON NOT NULL,
                idempotency_key VARCHAR(255) NOT NULL,
                request_hash VARCHAR(64) NOT NULL,
                status VARCHAR(30) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_orders_user_idempotency
                    UNIQUE (user_id, idempotency_key)
            )
        """)
    yield conn
    conn.close()

@pytest.fixture(autouse=True)
def clean_orders(db):
    with db.cursor() as cur:
        cur.execute("DELETE FROM orders")
    yield

def payload(quantity=2):
    return {
        "user_id": "integration-user",
        "vendor_id": "integration-vendor",
        "items": [{"item_id": "meal-7", "quantity": quantity}],
    }

def post_order(key, body):
    with httpx.Client(timeout=15) as client:
        return client.post(
            f"{API_URL}/api/orders",
            headers={"Idempotency-Key": key},
            json=body,
        )

def count_orders(db, user_id, key):
    with db.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM orders WHERE user_id = %s AND idempotency_key = %s",
            (user_id, key),
        )
        return cur.fetchone()[0]

def test_create_order_returns_201_and_persists_row(db):
    response = post_order("integration-create-1", payload())
    assert response.status_code == 201, response.text
    assert response.json()["id"]
    assert count_orders(db, "integration-user", "integration-create-1") == 1

def test_same_key_and_payload_returns_same_order(db):
    first = post_order("integration-retry-1", payload())
    second = post_order("integration-retry-1", payload())

    assert first.status_code == 201, first.text
    assert second.status_code == 200 or second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]
    assert count_orders(db, "integration-user", "integration-retry-1") == 1

def test_same_key_different_payload_returns_409(db):
    first = post_order("integration-conflict-1", payload(quantity=2))
    second = post_order("integration-conflict-1", payload(quantity=3))

    assert first.status_code == 201, first.text
    assert second.status_code == 409, second.text
    assert count_orders(db, "integration-user", "integration-conflict-1") == 1

def test_concurrent_same_key_requests_create_one_order(db):
    key = "integration-concurrent-1"
    body = payload()

    with ThreadPoolExecutor(max_workers=10) as executor:
        responses = list(executor.map(lambda _: post_order(key, body), range(10)))

    failures = [
        f"HTTP {r.status_code}: {r.text}"
        for r in responses
        if r.status_code not in (200, 201)
    ]
    assert not failures, failures

    order_ids = {r.json()["id"] for r in responses}
    assert len(order_ids) == 1
    assert count_orders(db, "integration-user", key) == 1
