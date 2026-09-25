"""Restaurant API endpoints for menu and order management."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from app.core.rbac import require_current_user, writable_hospital_id
from app.services.restaurant_service import restaurant_service

router = APIRouter(tags=["restaurant"])


class MenuItemResponse(BaseModel):
    """Menu item response."""
    id: str
    name: str
    description: Optional[str]
    category: str
    price: float
    is_available: bool
    preparation_time_minutes: int
    metadata: dict


class OrderItemRequest(BaseModel):
    """Order item request."""
    item_id: str
    quantity: int = Field(default=1, ge=1)
    notes: Optional[str] = None


class CreateOrderRequest(BaseModel):
    """Create order request."""
    customer_phone: str
    items: List[OrderItemRequest]
    customer_name: Optional[str] = None
    delivery_address: Optional[str] = None
    call_id: Optional[str] = None
    notes: Optional[str] = None


class OrderResponse(BaseModel):
    """Order response."""
    order_id: str
    total_amount: float
    status: str
    item_count: int


@router.get("/menu")
async def get_menu(
    hospital_id: str = Depends(writable_hospital_id),
    _: None = Depends(require_current_user)
):
    """Get all available menu items."""
    try:
        menu = restaurant_service.get_menu(hospital_id)
        return {
            "hospital_id": hospital_id,
            "menu": menu,
            "count": len(menu)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/menu/{item_id}")
async def get_menu_item(
    item_id: str,
    hospital_id: str = Depends(writable_hospital_id),
    _: None = Depends(require_current_user)
):
    """Get details for a specific menu item."""
    try:
        item = restaurant_service.get_item_details(hospital_id, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Menu item not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/calculate")
async def calculate_order_total(
    items: List[OrderItemRequest],
    hospital_id: str = Depends(writable_hospital_id),
    _: None = Depends(require_current_user)
):
    """Calculate total for a list of items without creating an order."""
    try:
        items_data = [{"item_id": item.item_id, "quantity": item.quantity} for item in items]
        result = restaurant_service.calculate_total(hospital_id, items_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders", response_model=OrderResponse)
async def create_order(
    request: CreateOrderRequest,
    hospital_id: str = Depends(writable_hospital_id),
    _: None = Depends(require_current_user)
):
    """Create a new order."""
    try:
        items_data = [
            {
                "item_id": item.item_id,
                "quantity": item.quantity,
                "notes": item.notes
            }
            for item in request.items
        ]
        
        order = restaurant_service.create_order(
            hospital_id=hospital_id,
            customer_phone=request.customer_phone,
            items=items_data,
            customer_name=request.customer_name,
            delivery_address=request.delivery_address,
            call_id=request.call_id,
            notes=request.notes,
        )
        return OrderResponse(**order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    hospital_id: str = Depends(writable_hospital_id),
    _: None = Depends(require_current_user)
):
    """Get order details and status."""
    try:
        order = restaurant_service.get_order_status(hospital_id, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    hospital_id: str = Depends(writable_hospital_id),
    _: None = Depends(require_current_user)
):
    """Cancel a pending order."""
    try:
        success = restaurant_service.cancel_order(hospital_id, order_id)
        if not success:
            raise HTTPException(status_code=400, detail="Order cannot be cancelled (not in pending status or not found)")
        return {"message": "Order cancelled successfully", "order_id": order_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/delivery-options")
async def get_delivery_options(
    hospital_id: str = Depends(writable_hospital_id),
    _: None = Depends(require_current_user)
):
    """Get available delivery options."""
    try:
        options = restaurant_service.get_delivery_options(hospital_id)
        return {
            "hospital_id": hospital_id,
            "options": options
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
