import pytest
from pydantic import ValidationError
from app.main import normalized_payload
from app.schemas import CreateOrderIn

def test_payload_hash_is_stable():
    payload = CreateOrderIn(user_id="user-101", vendor_id="vendor-12",
                            items=[{"item_id": "meal-7", "quantity": 2}])
    assert normalized_payload(payload)[0] == normalized_payload(payload)[0]

def test_quantity_must_be_positive():
    with pytest.raises(ValidationError):
        CreateOrderIn(user_id="user-101", vendor_id="vendor-12",
                      items=[{"item_id": "meal-7", "quantity": 0}])
