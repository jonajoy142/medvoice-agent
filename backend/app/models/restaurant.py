"""Restaurant models for menu items and orders.

Note: This codebase uses direct SQL queries through the repository pattern
rather than ORM relationships. These models are for type hints and reference only.
"""

from enum import Enum


class OrderStatus(str, Enum):
    """Order status enum."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# Type hints for restaurant entities (actual data is accessed via SQL queries)
class MenuItem:
    """Menu item entity (for type hints)."""
    id: str
    hospital_id: str
    name: str
    description: str | None
    category: str
    price: float
    is_available: bool
    preparation_time_minutes: int
    metadata: dict
    created_at: str
    updated_at: str


class Order:
    """Order entity (for type hints)."""
    id: str
    hospital_id: str
    call_id: str | None
    customer_phone: str
    customer_name: str | None
    delivery_address: str | None
    status: str
    total_amount: float
    currency: str
    notes: str | None
    metadata: dict
    created_at: str
    updated_at: str
    confirmed_at: str | None
    delivered_at: str | None


class OrderItem:
    """Order item entity (for type hints)."""
    id: str
    order_id: str
    menu_item_id: str
    quantity: int
    unit_price: float
    subtotal: float
    notes: str | None
    created_at: str
