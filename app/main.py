import hashlib
import json
from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from sqlalchemy.orm import Session
from .database import get_db
from .models import Order
from .schemas import CreateOrderIn

app = FastAPI(title="Hoplid Order Service", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/live")
def liveness():
    return {"status": "alive"}


@app.get("/health/ready")
def readiness(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )

def normalized_payload(payload: CreateOrderIn):
    data = payload.model_dump(mode="json")
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest(), data

def order_response(order: Order):
    return {
        "id": str(order.id), "user_id": order.user_id,
        "vendor_id": order.vendor_id, "items": order.items,
        "status": order.status, "created_at": order.created_at.isoformat(),
    }

@app.post("/api/orders", status_code=201)
def create_order(
    payload: CreateOrderIn,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    db: Session = Depends(get_db),
):
    digest, data = normalized_payload(payload)
    existing = db.scalar(select(Order).where(
        Order.user_id == data["user_id"], Order.idempotency_key == idempotency_key
    ))
    if existing:
        if existing.request_hash != digest:
            raise HTTPException(status_code=409, detail="Idempotency-Key already used with a different payload")
        return order_response(existing)

    order = Order(
        user_id=data["user_id"], vendor_id=data["vendor_id"], items=data["items"],
        idempotency_key=idempotency_key, request_hash=digest, status="confirmed",
    )
    db.add(order)
    try:
        db.commit()
        db.refresh(order)
        return order_response(order)
    except IntegrityError:
        # The DB unique constraint resolves concurrent attempts using the same key.
        db.rollback()
        existing = db.scalar(select(Order).where(
            Order.user_id == data["user_id"], Order.idempotency_key == idempotency_key
        ))
        if existing:
            if existing.request_hash != digest:
                raise HTTPException(status_code=409, detail="Idempotency-Key already used with a different payload")
            return order_response(existing)
        raise HTTPException(status_code=500, detail="Order could not be saved; retry using the same key")
