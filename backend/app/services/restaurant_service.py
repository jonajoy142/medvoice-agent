"""Restaurant service for menu and order management."""

from typing import List, Optional, Dict, Any
from sqlalchemy import text
from uuid import UUID
from decimal import Decimal

from app.db.session import db_session
from app.models.restaurant import MenuItem, Order, OrderItem, OrderStatus


class RestaurantService:
    """Service for restaurant menu and order operations."""
    
    def get_menu(self, hospital_id: str) -> List[Dict[str, Any]]:
        """Get all available menu items for a hospital."""
        with db_session() as db:
            query = text("""
                SELECT id, name, description, category, price, is_available, 
                       preparation_time_minutes, metadata
                FROM menu_items
                WHERE hospital_id = :hospital_id AND is_available = true
                ORDER BY category, name
            """)
            result = db.execute(query, {"hospital_id": hospital_id})
            return [dict(row._mapping) for row in result]
    
    def get_item_details(self, hospital_id: str, item_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific menu item."""
        with db_session() as db:
            query = text("""
                SELECT id, name, description, category, price, is_available, 
                       preparation_time_minutes, metadata
                FROM menu_items
                WHERE hospital_id = :hospital_id AND id = :item_id
            """)
            result = db.execute(query, {"hospital_id": hospital_id, "item_id": item_id}).first()
            return dict(result._mapping) if result else None
    
    def check_item_availability(self, hospital_id: str, item_name: str) -> bool:
        """Check if a menu item is available by name."""
        with db_session() as db:
            query = text("""
                SELECT is_available
                FROM menu_items
                WHERE hospital_id = :hospital_id AND name ILIKE :item_name
                LIMIT 1
            """)
            result = db.execute(query, {"hospital_id": hospital_id, "item_name": f"%{item_name}%"}).first()
            return result[0] if result else False
    
    def create_order(
        self,
        hospital_id: str,
        customer_phone: str,
        items: List[Dict[str, Any]],
        customer_name: Optional[str] = None,
        delivery_address: Optional[str] = None,
        call_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new order with items."""
        with db_session() as db:
            # Calculate total
            total_amount = Decimal("0.00")
            order_items_data = []
            
            for item in items:
                menu_item = db.execute(
                    text("SELECT id, price FROM menu_items WHERE hospital_id = :hospital_id AND id = :item_id"),
                    {"hospital_id": hospital_id, "item_id": item["item_id"]}
                ).first()
                
                if not menu_item:
                    raise ValueError(f"Menu item {item['item_id']} not found")
                
                quantity = item.get("quantity", 1)
                unit_price = Decimal(str(menu_item[1]))
                subtotal = unit_price * quantity
                total_amount += subtotal
                
                order_items_data.append({
                    "menu_item_id": menu_item[0],
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "subtotal": subtotal,
                    "notes": item.get("notes")
                })
            
            # Create order
            order_result = db.execute(
                text("""
                    INSERT INTO orders (hospital_id, call_id, customer_phone, customer_name, 
                                       delivery_address, status, total_amount, notes, metadata)
                    VALUES (:hospital_id, :call_id, :customer_phone, :customer_name,
                            :delivery_address, :status, :total_amount, :notes, :metadata)
                    RETURNING id
                """),
                {
                    "hospital_id": hospital_id,
                    "call_id": call_id,
                    "customer_phone": customer_phone,
                    "customer_name": customer_name,
                    "delivery_address": delivery_address,
                    "status": OrderStatus.PENDING.value,
                    "total_amount": total_amount,
                    "notes": notes,
                    "metadata": {}
                }
            ).scalar()
            
            # Create order items
            for item_data in order_items_data:
                db.execute(
                    text("""
                        INSERT INTO order_items (order_id, menu_item_id, quantity, unit_price, subtotal, notes)
                        VALUES (:order_id, :menu_item_id, :quantity, :unit_price, :subtotal, :notes)
                    """),
                    {**item_data, "order_id": order_result}
                )
            
            return {
                "order_id": str(order_result),
                "total_amount": float(total_amount),
                "status": OrderStatus.PENDING.value,
                "item_count": len(order_items_data)
            }
    
    def get_order_status(self, hospital_id: str, order_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an order."""
        with db_session() as db:
            query = text("""
                SELECT o.id, o.customer_phone, o.customer_name, o.status, o.total_amount,
                       o.created_at, o.confirmed_at, o.delivered_at,
                       json_agg(
                           json_build_object(
                               'item_name', mi.name,
                               'quantity', oi.quantity,
                               'unit_price', oi.unit_price,
                               'subtotal', oi.subtotal
                           )
                       ) as items
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                LEFT JOIN menu_items mi ON oi.menu_item_id = mi.id
                WHERE o.hospital_id = :hospital_id AND o.id = :order_id
                GROUP BY o.id
            """)
            result = db.execute(query, {"hospital_id": hospital_id, "order_id": order_id}).first()
            return dict(result._mapping) if result else None
    
    def cancel_order(self, hospital_id: str, order_id: str) -> bool:
        """Cancel an order if it's in pending status."""
        with db_session() as db:
            result = db.execute(
                text("""
                    UPDATE orders
                    SET status = :cancelled_status, updated_at = now()
                    WHERE hospital_id = :hospital_id AND id = :order_id AND status = :pending_status
                    RETURNING id
                """),
                {
                    "hospital_id": hospital_id,
                    "order_id": order_id,
                    "pending_status": OrderStatus.PENDING.value,
                    "cancelled_status": OrderStatus.CANCELLED.value
                }
            )
            return result.first() is not None
    
    def get_delivery_options(self, hospital_id: str) -> List[Dict[str, Any]]:
        """Get available delivery options."""
        with db_session() as db:
            query = text("""
                SELECT metadata->'delivery' as delivery_options
                FROM hospital_settings
                WHERE hospital_id = :hospital_id
                LIMIT 1
            """)
            result = db.execute(query, {"hospital_id": hospital_id}).first()
            if result and result[0]:
                return result[0]
            # Default delivery options
            return [
                {"type": "pickup", "name": "Store Pickup", "time_minutes": 15},
                {"type": "delivery", "name": "Home Delivery", "time_minutes": 45, "fee": 50}
            ]
    
    def validate_address(self, address: str) -> Dict[str, Any]:
        """Validate delivery address (basic validation)."""
        if not address or len(address.strip()) < 10:
            return {"valid": False, "reason": "Address too short"}
        return {"valid": True, "reason": "Address looks valid"}
    
    def calculate_total(self, hospital_id: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate total for a list of items without creating order."""
        with db_session() as db:
            total = Decimal("0.00")
            item_details = []
            
            for item in items:
                menu_item = db.execute(
                    text("SELECT id, name, price FROM menu_items WHERE hospital_id = :hospital_id AND id = :item_id"),
                    {"hospital_id": hospital_id, "item_id": item["item_id"]}
                ).first()
                
                if not menu_item:
                    continue
                
                quantity = item.get("quantity", 1)
                unit_price = Decimal(str(menu_item[2]))
                subtotal = unit_price * quantity
                total += subtotal
                
                item_details.append({
                    "name": menu_item[1],
                    "quantity": quantity,
                    "unit_price": float(unit_price),
                    "subtotal": float(subtotal)
                })
            
            return {
                "total": float(total),
                "items": item_details,
                "item_count": len(item_details)
            }


restaurant_service = RestaurantService()
