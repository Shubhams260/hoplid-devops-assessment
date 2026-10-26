
from contextlib import asynccontextmanager
import hashlib
import hmac
import json
import os

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import engine, get_db
from .models import Order
from .schemas import CreateOrderIn


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.shutting_down = False
    try:
        yield
    finally:
        app.state.shutting_down = True
        engine.dispose()


app = FastAPI(
    title="Hoplid Order Service",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def reject_new_requests_while_draining(request: Request, call_next):
    allowed_paths = {
        "/health",
        "/health/live",
        "/health/ready",
        "/internal/drain",
    }

    if (
        getattr(request.app.state, "shutting_down", False)
        and request.url.path not in allowed_paths
    ):
        return JSONResponse(
            status_code=503,
            content={"detail": "Service is shutting down"},
            headers={"Connection": "close"},
        )

    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/live")
def liveness():
    return {"status": "alive"}


@app.post("/internal/drain")
def start_draining(
    request: Request,
    x_drain_token: str = Header(alias="X-Drain-Token"),
):
    expected_token = os.getenv("DRAIN_TOKEN", "")
    if not expected_token or not hmac.compare_digest(
        x_drain_token, expected_token
    ):
        raise HTTPException(status_code=403, detail="Invalid drain token")

    request.app.state.shutting_down = True
    return {"status": "draining"}


@app.get("/health/ready")
def readiness(request: Request, db: Session = Depends(get_db)):
    if request.app.state.shutting_down:
        raise HTTPException(
            status_code=503,
            detail="Service is shutting down",
        )

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
        "id": str(order.id),
        "user_id": order.user_id,
        "vendor_id": order.vendor_id,
        "items": order.items,
        "status": order.status,
        "created_at": order.created_at.isoformat(),
    }


@app.post("/api/orders", status_code=201)
def create_order(
    payload: CreateOrderIn,
    idempotency_key: str = Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=255,
    ),
    db: Session = Depends(get_db),
):
    digest, data = normalized_payload(payload)

    existing = db.scalar(
        select(Order).where(
            Order.user_id == data["user_id"],
            Order.idempotency_key == idempotency_key,
        )
    )

    if existing:
        if existing.request_hash != digest:
            raise HTTPException(
                status_code=409,
                detail="Idempotency-Key already used with a different payload",
            )
        return order_response(existing)

    order = Order(
        user_id=data["user_id"],
        vendor_id=data["vendor_id"],
        items=data["items"],
        idempotency_key=idempotency_key,
        request_hash=digest,
        status="confirmed",
    )
    db.add(order)

    try:
        db.commit()
        db.refresh(order)
        return order_response(order)

    except IntegrityError:
        db.rollback()

        existing = db.scalar(
            select(Order).where(
                Order.user_id == data["user_id"],
                Order.idempotency_key == idempotency_key,
            )
        )

        if existing:
            if existing.request_hash != digest:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Idempotency-Key already used with a different payload"
                    ),
                )
            return order_response(existing)

        raise HTTPException(
            status_code=500,
            detail="Order could not be saved; retry using the same key",
        )
