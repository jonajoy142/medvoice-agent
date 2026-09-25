"""Seed Demo Pizza restaurant with menu and sample data."""

from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import db_session


DEMO_PIZZA_MENU = [
    {
        "name": "Margherita Pizza",
        "description": "Classic pizza with fresh tomatoes, mozzarella, and basil",
        "category": "pizza",
        "price": 250,
        "preparation_time_minutes": 15,
    },
    {
        "name": "Chicken Pizza",
        "description": "Topped with spiced chicken and vegetables",
        "category": "pizza",
        "price": 320,
        "preparation_time_minutes": 20,
    },
    {
        "name": "Veg Pizza",
        "description": "Loaded with fresh vegetables and cheese",
        "category": "pizza",
        "price": 280,
        "preparation_time_minutes": 18,
    },
    {
        "name": "Coke",
        "description": "Chilled Coca-Cola 500ml",
        "category": "beverage",
        "price": 40,
        "preparation_time_minutes": 2,
    },
    {
        "name": "Pepsi",
        "description": "Chilled Pepsi 500ml",
        "category": "beverage",
        "price": 40,
        "preparation_time_minutes": 2,
    },
    {
        "name": "Garlic Bread",
        "description": "Crispy garlic bread with cheese",
        "category": "sides",
        "price": 120,
        "preparation_time_minutes": 10,
    },
]


def main() -> None:
    """Seed Demo Pizza restaurant."""
    hospital_id = os.getenv("SEED_HOSPITAL_ID")
    
    if not hospital_id:
        # Create or find Demo Pizza hospital
        with db_session() as db:
            existing = db.execute(
                text("SELECT id FROM hospitals WHERE slug='demo-pizza' LIMIT 1")
            ).scalar()
            
            if existing:
                hospital_id = str(existing)
                print(f"Using existing Demo Pizza hospital: {hospital_id}")
            else:
                hospital_id = str(uuid4())
                db.execute(
                    text("""
                        INSERT INTO hospitals (id, name, slug, timezone, status, plan, admin_email)
                        VALUES (:id, 'Demo Pizza', 'demo-pizza', 'Asia/Kolkata', 'active', 'pilot', 'admin@demopizza.com')
                    """),
                    {"id": hospital_id}
                )
                db.execute(
                    text("""
                        INSERT INTO subscriptions (hospital_id, plan, status, billing_email)
                        VALUES (:id, 'pilot', 'trialing', 'admin@demopizza.com')
                        ON CONFLICT DO NOTHING
                    """),
                    {"id": hospital_id}
                )
                db.execute(
                    text("""
                        INSERT INTO hospital_settings (hospital_id, business_hours, telephony, voice, ai, security)
                        VALUES (:id, CAST(:hours AS jsonb), CAST(:telephony AS jsonb), CAST(:voice AS jsonb), CAST(:ai AS jsonb), CAST(:security AS jsonb))
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "id": hospital_id,
                        "hours": json.dumps({"mon_sun": "11:00-23:00"}),
                        "telephony": json.dumps({"provider": "exotel", "status": "not_configured"}),
                        "voice": json.dumps({"provider": "openai", "languages": ["en-IN", "ml-IN"]}),
                        "ai": json.dumps({"provider": "openai", "low_confidence_threshold": 0.72}),
                        "security": json.dumps({"rbac": True, "rls": True}),
                    }
                )
                print(f"Created Demo Pizza hospital: {hospital_id}")
    
    # Seed menu items
    with db_session() as db:
        for item in DEMO_PIZZA_MENU:
            existing = db.execute(
                text("""
                    SELECT id FROM menu_items 
                    WHERE hospital_id = :hospital_id AND name = :name 
                    LIMIT 1
                """),
                {"hospital_id": hospital_id, "name": item["name"]}
            ).scalar()
            
            if existing:
                print(f"Menu item already exists: {item['name']}")
                continue
            
            db.execute(
                text("""
                    INSERT INTO menu_items (hospital_id, name, description, category, price, 
                                          is_available, preparation_time_minutes, metadata)
                    VALUES (:hospital_id, :name, :description, :category, :price,
                            true, :preparation_time_minutes, :metadata)
                """),
                {
                    "hospital_id": hospital_id,
                    "name": item["name"],
                    "description": item["description"],
                    "category": item["category"],
                    "price": item["price"],
                    "preparation_time_minutes": item["preparation_time_minutes"],
                    "metadata": json.dumps({})
                }
            )
            print(f"Added menu item: {item['name']}")
    
    # Create restaurant agent
    with db_session() as db:
        existing_agent = db.execute(
            text("""
                SELECT id FROM agents 
                WHERE hospital_id = :hospital_id AND name = 'Pizza Order Agent' 
                LIMIT 1
            """),
            {"hospital_id": hospital_id}
        ).scalar()
        
        if not existing_agent:
            agent_id = db.execute(
                text("""
                    INSERT INTO agents (hospital_id, name, description, status, language, 
                                       voice_provider, voice_name, greeting, system_prompt,
                                       fallback_behavior, transfer_phone_number, working_hours,
                                       stt_provider, llm_provider, tts_provider, llm_model,
                                       supported_languages, enabled_tools, business_config)
                    VALUES (:hospital_id, :name, :description, 'active', :language,
                            'openai', 'alloy', :greeting, :system_prompt,
                            :fallback_behavior, :transfer_phone_number, CAST(:working_hours AS jsonb),
                            'openai', 'openai', 'openai', 'gpt-4o-mini',
                            CAST(:supported_languages AS jsonb), CAST(:enabled_tools AS jsonb), CAST(:business_config AS jsonb))
                    RETURNING id
                """),
                {
                    "hospital_id": hospital_id,
                    "name": "Pizza Order Agent",
                    "description": "AI agent for taking pizza orders over phone",
                    "language": "en-IN",
                    "greeting": "Hello! Welcome to Demo Pizza. I can help you order our delicious pizzas. What would you like to order today?",
                    "system_prompt": """You are a friendly pizza ordering assistant for Demo Pizza. Your role is to:

1. Help customers understand the menu
2. Take orders clearly and accurately
3. Confirm order details before finalizing
4. Handle questions about ingredients, prices, and preparation time
5. Be polite and efficient

Menu items available:
- Margherita Pizza (₹250) - Classic with tomatoes, mozzarella, basil
- Chicken Pizza (₹320) - Spiced chicken with vegetables  
- Veg Pizza (₹280) - Fresh vegetables and cheese
- Coke (₹40) - 500ml
- Pepsi (₹40) - 500ml
- Garlic Bread (₹120) - Crispy with cheese

Always confirm the order by repeating:
- Items ordered with quantities
- Total amount
- Ask for confirmation before placing the order

If customers ask about things not on the menu, politely explain what's available.
Be concise but friendly. Use simple language.""",
                    "fallback_behavior": "transfer_to_human",
                    "transfer_phone_number": None,
                    "working_hours": json.dumps({"mon_sun": "11:00-23:00"}),
                    "supported_languages": json.dumps(["en-IN", "ml-IN"]),
                    "enabled_tools": json.dumps([
                        "get_menu",
                        "get_item_details", 
                        "check_item_availability",
                        "add_item",
                        "calculate_total",
                        "create_order",
                        "get_order_status"
                    ]),
                    "business_config": json.dumps({
                        "type": "restaurant",
                        "restaurant_name": "Demo Pizza",
                        "currency": "INR",
                        "delivery_options": ["pickup", "delivery"]
                    })
                }
            ).scalar()
            print(f"Created Pizza Order Agent: {agent_id}")
        else:
            print(f"Pizza Order Agent already exists: {existing_agent}")
    
    print(f"\nDemo Pizza seeded successfully!")
    print(f"Hospital ID: {hospital_id}")
    print(f"Menu items: {len(DEMO_PIZZA_MENU)}")
    print(f"\nTo test: Set hospital_id={hospital_id} in your Exotel custom_parameters")


if __name__ == "__main__":
    main()
