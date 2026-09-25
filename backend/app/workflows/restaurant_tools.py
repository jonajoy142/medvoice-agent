"""Restaurant tools for LLM function calling."""

from typing import Dict, Any, List, Optional
from app.services.restaurant_service import restaurant_service


class RestaurantTools:
    """Restaurant tools that can be called by the LLM."""
    
    @staticmethod
    def get_menu(hospital_id: str) -> Dict[str, Any]:
        """Get the restaurant menu with all available items."""
        try:
            menu = restaurant_service.get_menu(hospital_id)
            return {
                "success": True,
                "menu": menu,
                "message": f"Found {len(menu)} menu items"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve menu"
            }
    
    @staticmethod
    def get_item_details(hospital_id: str, item_name: str) -> Dict[str, Any]:
        """Get details for a specific menu item by name."""
        try:
            # First try to find by name
            menu = restaurant_service.get_menu(hospital_id)
            matching_items = [item for item in menu if item_name.lower() in item["name"].lower()]
            
            if matching_items:
                item = matching_items[0]
                return {
                    "success": True,
                    "item": item,
                    "message": f"Found: {item['name']} - ₹{item['price']}"
                }
            else:
                return {
                    "success": False,
                    "error": "Item not found",
                    "message": f"Could not find '{item_name}' in menu"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get item details"
            }
    
    @staticmethod
    def check_item_availability(hospital_id: str, item_name: str) -> Dict[str, Any]:
        """Check if a menu item is available."""
        try:
            is_available = restaurant_service.check_item_availability(hospital_id, item_name)
            if is_available:
                return {
                    "success": True,
                    "available": True,
                    "message": f"{item_name} is available"
                }
            else:
                return {
                    "success": True,
                    "available": False,
                    "message": f"{item_name} is not currently available"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to check availability"
            }
    
    @staticmethod
    def calculate_total(hospital_id: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate total cost for a list of items.
        
        Args:
            hospital_id: Hospital ID
            items: List of dicts with 'item_id' and 'quantity' keys
        """
        try:
            result = restaurant_service.calculate_total(hospital_id, items)
            return {
                "success": True,
                "total": result["total"],
                "items": result["items"],
                "item_count": result["item_count"],
                "message": f"Total: ₹{result['total']} for {result['item_count']} items"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to calculate total"
            }
    
    @staticmethod
    def create_order(
        hospital_id: str,
        customer_phone: str,
        items: List[Dict[str, Any]],
        customer_name: Optional[str] = None,
        delivery_address: Optional[str] = None,
        call_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new order.
        
        Args:
            hospital_id: Hospital ID
            customer_phone: Customer phone number
            items: List of dicts with 'item_id' and 'quantity' keys
            customer_name: Optional customer name
            delivery_address: Optional delivery address
            call_id: Optional associated call ID
            notes: Optional order notes
        """
        try:
            order = restaurant_service.create_order(
                hospital_id=hospital_id,
                customer_phone=customer_phone,
                items=items,
                customer_name=customer_name,
                delivery_address=delivery_address,
                call_id=call_id,
                notes=notes,
            )
            return {
                "success": True,
                "order_id": order["order_id"],
                "total_amount": order["total_amount"],
                "status": order["status"],
                "item_count": order["item_count"],
                "message": f"Order created successfully! Total: ₹{order['total_amount']}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create order"
            }
    
    @staticmethod
    def get_order_status(hospital_id: str, order_id: str) -> Dict[str, Any]:
        """Get the status of an existing order."""
        try:
            order = restaurant_service.get_order_status(hospital_id, order_id)
            if order:
                return {
                    "success": True,
                    "order": order,
                    "message": f"Order status: {order['status']}"
                }
            else:
                return {
                    "success": False,
                    "error": "Order not found",
                    "message": f"Could not find order {order_id}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get order status"
            }
    
    @staticmethod
    def get_delivery_options(hospital_id: str) -> Dict[str, Any]:
        """Get available delivery options."""
        try:
            options = restaurant_service.get_delivery_options(hospital_id)
            return {
                "success": True,
                "options": options,
                "message": f"Found {len(options)} delivery options"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get delivery options"
            }


# Tool function registry for LLM function calling
RESTAURANT_TOOL_FUNCTIONS = {
    "get_menu": {
        "function": RestaurantTools.get_menu,
        "description": "Get the restaurant menu with all available items, prices, and descriptions",
        "parameters": {
            "type": "object",
            "properties": {
                "hospital_id": {
                    "type": "string",
                    "description": "Hospital/restaurant ID"
                }
            },
            "required": ["hospital_id"]
        }
    },
    "get_item_details": {
        "function": RestaurantTools.get_item_details,
        "description": "Get detailed information about a specific menu item",
        "parameters": {
            "type": "object",
            "properties": {
                "hospital_id": {
                    "type": "string",
                    "description": "Hospital/restaurant ID"
                },
                "item_name": {
                    "type": "string",
                    "description": "Name of the menu item to look up"
                }
            },
            "required": ["hospital_id", "item_name"]
        }
    },
    "check_item_availability": {
        "function": RestaurantTools.check_item_availability,
        "description": "Check if a menu item is currently available",
        "parameters": {
            "type": "object",
            "properties": {
                "hospital_id": {
                    "type": "string",
                    "description": "Hospital/restaurant ID"
                },
                "item_name": {
                    "type": "string",
                    "description": "Name of the menu item to check"
                }
            },
            "required": ["hospital_id", "item_name"]
        }
    },
    "calculate_total": {
        "function": RestaurantTools.calculate_total,
        "description": "Calculate the total cost for a list of items before placing the order",
        "parameters": {
            "type": "object",
            "properties": {
                "hospital_id": {
                    "type": "string",
                    "description": "Hospital/restaurant ID"
                },
                "items": {
                    "type": "array",
                    "description": "List of items with item_id and quantity",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_id": {"type": "string"},
                            "quantity": {"type": "integer"}
                        }
                    }
                }
            },
            "required": ["hospital_id", "items"]
        }
    },
    "create_order": {
        "function": RestaurantTools.create_order,
        "description": "Create a new order with the specified items",
        "parameters": {
            "type": "object",
            "properties": {
                "hospital_id": {
                    "type": "string",
                    "description": "Hospital/restaurant ID"
                },
                "customer_phone": {
                    "type": "string",
                    "description": "Customer phone number"
                },
                "items": {
                    "type": "array",
                    "description": "List of items with item_id and quantity",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_id": {"type": "string"},
                            "quantity": {"type": "integer"}
                        }
                    }
                },
                "customer_name": {
                    "type": "string",
                    "description": "Optional customer name"
                },
                "delivery_address": {
                    "type": "string",
                    "description": "Optional delivery address"
                },
                "call_id": {
                    "type": "string",
                    "description": "Optional associated call ID"
                },
                "notes": {
                    "type": "string",
                    "description": "Optional order notes"
                }
            },
            "required": ["hospital_id", "customer_phone", "items"]
        }
    },
    "get_order_status": {
        "function": RestaurantTools.get_order_status,
        "description": "Get the current status of an existing order",
        "parameters": {
            "type": "object",
            "properties": {
                "hospital_id": {
                    "type": "string",
                    "description": "Hospital/restaurant ID"
                },
                "order_id": {
                    "type": "string",
                    "description": "Order ID to check"
                }
            },
            "required": ["hospital_id", "order_id"]
        }
    },
    "get_delivery_options": {
        "function": RestaurantTools.get_delivery_options,
        "description": "Get available delivery options (pickup, delivery, etc.)",
        "parameters": {
            "type": "object",
            "properties": {
                "hospital_id": {
                    "type": "string",
                    "description": "Hospital/restaurant ID"
                }
            },
            "required": ["hospital_id"]
        }
    }
}


restaurant_tools = RestaurantTools()
