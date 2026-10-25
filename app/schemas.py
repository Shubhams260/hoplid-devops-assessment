from pydantic import BaseModel, Field, ConfigDict

class OrderItemIn(BaseModel):
    item_id: str = Field(min_length=1, max_length=100)
    quantity: int = Field(ge=1, le=100)

class CreateOrderIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str = Field(min_length=1, max_length=100)
    vendor_id: str = Field(min_length=1, max_length=100)
    items: list[OrderItemIn] = Field(min_length=1, max_length=100)
