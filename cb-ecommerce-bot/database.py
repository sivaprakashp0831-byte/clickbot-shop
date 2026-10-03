"""
Deterministic mock database for the rule-based e-commerce chatbot.
No ML/NLP/LLM components are used.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, Optional


PRODUCTS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "electronics": {
        "phone-x1": {
            "id": "phone-x1",
            "name": "Nova X1 Smartphone",
            "price": 24999.0,
            "image_url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=900&q=85",
            "description": "6.5-inch display, 128 GB storage, dual camera, and all-day battery."
        },
        "headphones-hd": {
            "id": "headphones-hd",
            "name": "Pulse HD Headphones",
            "price": 3499.0,
            "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=85",
            "description": "Wireless over-ear headphones with active noise reduction and 30-hour playback."
        },
        "watch-fit": {
            "id": "watch-fit",
            "name": "FitTime Smart Watch",
            "price": 5999.0,
            "image_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=900&q=85",
            "description": "Fitness tracking, notifications, heart-rate monitoring, and a bright touch display."
        }
    },
    "apparel": {
        "shirt-cotton": {
            "id": "shirt-cotton",
            "name": "Classic Cotton Shirt",
            "price": 1299.0,
            "image_url": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=900&q=85",
            "description": "Comfortable regular-fit cotton shirt suitable for everyday wear."
        },
        "hoodie-core": {
            "id": "hoodie-core",
            "name": "Core Fleece Hoodie",
            "price": 1899.0,
            "image_url": "https://images.unsplash.com/photo-1556821840-3a63f95609a7?auto=format&fit=crop&w=900&q=85",
            "description": "Soft fleece hoodie with a classic silhouette and front pocket."
        },
        "sneakers-run": {
            "id": "sneakers-run",
            "name": "RunFlex Sneakers",
            "price": 2799.0,
            "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=85",
            "description": "Lightweight everyday sneakers with cushioned support and flexible outsole."
        }
    },
    "home": {
        "lamp-desk": {
            "id": "lamp-desk",
            "name": "Glow Desk Lamp",
            "price": 1499.0,
            "image_url": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=900&q=85",
            "description": "Adjustable LED desk lamp with three brightness levels and a compact base."
        },
        "bottle-steel": {
            "id": "bottle-steel",
            "name": "Steel Insulated Bottle",
            "price": 899.0,
            "image_url": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?auto=format&fit=crop&w=900&q=85",
            "description": "Leak-resistant insulated bottle designed to keep drinks cool or warm for hours."
        },
        "organizer-box": {
            "id": "organizer-box",
            "name": "Modular Storage Box",
            "price": 749.0,
            "image_url": "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?auto=format&fit=crop&w=900&q=85",
            "description": "Stackable storage box for neat organization of home and desk essentials."
        }
    }
}

CATEGORIES = {
    "electronics": {"id": "electronics", "name": "Electronics", "icon": "📱"},
    "apparel": {"id": "apparel", "name": "Apparel", "icon": "👕"},
    "home": {"id": "home", "name": "Home", "icon": "🏠"},
}

ORDERS = {
    "ORD1001": {
        "order_id": "ORD1001",
        "session_id": "demo-active-session",
        "status": "Out for delivery",
        "eta": "Today, 6:00 PM – 9:00 PM",
        "items": ["Pulse HD Headphones"],
        "total": 3499.0,
        "updated_at": "2026-10-03T13:15:00+00:00"
    }
}

ORDERS_BY_SESSION: Dict[str, str] = {}

# Explicit state/choice decision tree.
ESCAPE_ROUTE = {"text": "⏮️ Main Menu", "next_state": "main_menu"}

STATE_TREE = {
    "main_menu": {
        "message": "Welcome! Choose what you want to do.",
        "choices": [
            {"choice_id": "browse_categories", "text": "🛍️ Browse Products", "next_state": "categories"},
            {"choice_id": "view_cart", "text": "🛒 View Cart", "next_state": "cart"},
            {"choice_id": "checkout", "text": "💳 Checkout", "next_state": "checkout"},
            {"choice_id": "track_order", "text": "📦 Track Order", "next_state": "order_status", "requires_active_order": True},
        ],
    },
    "categories": {
        "message": "Select a category.",
        "choices": [
            {"choice_id": "category_electronics", "text": "📱 Electronics", "next_state": "electronics"},
            {"choice_id": "category_apparel", "text": "👕 Apparel", "next_state": "apparel"},
            {"choice_id": "category_home", "text": "🏠 Home", "next_state": "home"},
            {"choice_id": "back_main_categories", **ESCAPE_ROUTE},
        ],
    },
    "electronics": {
        "message": "Electronics: choose a product.",
        "choices": [
            {"choice_id": "product_phone_x1", "text": "Nova X1 Smartphone", "next_state": "product_phone_x1"},
            {"choice_id": "product_headphones_hd", "text": "Pulse HD Headphones", "next_state": "product_headphones_hd"},
            {"choice_id": "product_watch_fit", "text": "FitTime Smart Watch", "next_state": "product_watch_fit"},
            {"choice_id": "back_categories_electronics", **ESCAPE_ROUTE},
        ],
    },
    "apparel": {
        "message": "Apparel: choose a product.",
        "choices": [
            {"choice_id": "product_shirt_cotton", "text": "Classic Cotton Shirt", "next_state": "product_shirt_cotton"},
            {"choice_id": "product_hoodie_core", "text": "Core Fleece Hoodie", "next_state": "product_hoodie_core"},
            {"choice_id": "product_sneakers_run", "text": "RunFlex Sneakers", "next_state": "product_sneakers_run"},
            {"choice_id": "back_categories_apparel", **ESCAPE_ROUTE},
        ],
    },
    "home": {
        "message": "Home: choose a product.",
        "choices": [
            {"choice_id": "product_lamp_desk", "text": "Glow Desk Lamp", "next_state": "product_lamp_desk"},
            {"choice_id": "product_bottle_steel", "text": "Steel Insulated Bottle", "next_state": "product_bottle_steel"},
            {"choice_id": "product_organizer_box", "text": "Modular Storage Box", "next_state": "product_organizer_box"},
            {"choice_id": "back_categories_home", **ESCAPE_ROUTE},
        ],
    },
    "cart": {
        "message": "Your cart is ready to review.",
        "choices": [
            {"choice_id": "cart_checkout", "text": "💳 Continue to Checkout", "next_state": "checkout"},
            {"choice_id": "cart_browse", "text": "🛍️ Continue Shopping", "next_state": "categories"},
            {"choice_id": "cart_main", **ESCAPE_ROUTE},
        ],
    },
    "checkout": {
        "message": "Checkout: enter your email address.",
        "choices": [
            {"choice_id": "checkout_start", "text": "✉️ Enter Email", "next_state": "checkout_email", "input_type": "email"},
            {"choice_id": "checkout_main", **ESCAPE_ROUTE},
        ],
    },
    "checkout_email": {
        "message": "Enter a valid email address.",
        "choices": [
            {"choice_id": "email_submit", "text": "Submit Email", "next_state": "checkout_phone", "input_type": "email"},
            {"choice_id": "email_cancel", **ESCAPE_ROUTE},
        ],
        "input_type": "email",
    },
    "checkout_phone": {
        "message": "Enter your phone number in international format, for example +919876543210.",
        "choices": [
            {"choice_id": "phone_submit", "text": "Submit Phone", "next_state": "checkout_confirm", "input_type": "phone"},
            {"choice_id": "phone_cancel", **ESCAPE_ROUTE},
        ],
        "input_type": "phone",
    },
    "checkout_confirm": {
        "message": "Review the checkout and confirm the order.",
        "choices": [
            {"choice_id": "place_order", "text": "✅ Place Order", "next_state": "order_created"},
            {"choice_id": "confirm_back", "text": "✏️ Edit Contact Details", "next_state": "checkout_email"},
            {"choice_id": "confirm_main", **ESCAPE_ROUTE},
        ],
    },
    "order_created": {
        "message": "Your order has been created successfully.",
        "choices": [
            {"choice_id": "created_track", "text": "📦 Track Order", "next_state": "order_status"},
            {"choice_id": "created_shop", "text": "🛍️ Shop More", "next_state": "categories"},
            {"choice_id": "created_main", **ESCAPE_ROUTE},
        ],
    },
    "order_status": {
        "message": "Here is the latest status for your active order.",
        "choices": [
            {"choice_id": "status_main", **ESCAPE_ROUTE},
            {"choice_id": "status_shop", "text": "🛍️ Shop More", "next_state": "categories"},
        ],
    },
}

for product_state, product_id in {
    "product_phone_x1": "phone-x1",
    "product_headphones_hd": "headphones-hd",
    "product_watch_fit": "watch-fit",
    "product_shirt_cotton": "shirt-cotton",
    "product_hoodie_core": "hoodie-core",
    "product_sneakers_run": "sneakers-run",
    "product_lamp_desk": "lamp-desk",
    "product_bottle_steel": "bottle-steel",
    "product_organizer_box": "organizer-box",
}.items():
    STATE_TREE[product_state] = {
        "message": PRODUCTS[next(category for category, items in PRODUCTS.items() if product_id in items)][product_id]["name"],
        "choices": [
            {"choice_id": f"add_{product_id.replace('-', '_')}", "text": "🛒 Add to Cart", "next_state": "cart"},
            {"choice_id": f"buy_{product_id.replace('-', '_')}", "text": "⚡ Buy Now", "next_state": "checkout"},
            {"choice_id": f"back_product_{product_id.replace('-', '_')}", **ESCAPE_ROUTE},
        ],
        "product_id": product_id,
    }

_SESSION_LOCK = RLock()
SESSIONS: Dict[str, Dict[str, Any]] = {}


def get_or_create_session(session_id: str) -> Dict[str, Any]:
    with _SESSION_LOCK:
        if session_id not in SESSIONS:
            SESSIONS[session_id] = {
                "session_id": session_id,
                "state": "main_menu",
                "email": None,
                "phone": None,
                "cart": [],
                "active_order_id": ORDERS_BY_SESSION.get(session_id),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        return deepcopy(SESSIONS[session_id])


def save_session(session: Dict[str, Any]) -> None:
    with _SESSION_LOCK:
        session["updated_at"] = datetime.now(timezone.utc).isoformat()
        SESSIONS[session["session_id"]] = deepcopy(session)


def get_order_for_session(session_id: str) -> Optional[Dict[str, Any]]:
    session = get_or_create_session(session_id)
    order_id = session.get("active_order_id") or ORDERS_BY_SESSION.get(session_id)
    if not order_id:
        return None
    return deepcopy(ORDERS.get(order_id))


def create_order(session: Dict[str, Any]) -> Dict[str, Any]:
    with _SESSION_LOCK:
        numeric = 1000 + len(ORDERS) + 1
        order_id = f"ORD{numeric}"
        cart = session.get("cart", [])
        item_names = [item["name"] for item in cart] or ["Nova X1 Smartphone"]
        total = sum(float(item["price"]) for item in cart) or 24999.0
        order = {
            "order_id": order_id,
            "session_id": session["session_id"],
            "status": "Order confirmed",
            "eta": "Expected delivery in 2–4 business days",
            "items": item_names,
            "total": total,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        ORDERS[order_id] = order
        ORDERS_BY_SESSION[session["session_id"]] = order_id
        session["active_order_id"] = order_id
        session["cart"] = []
        return deepcopy(order)


def add_product_to_cart(session: Dict[str, Any], product_id: str) -> Optional[Dict[str, Any]]:
    for category in PRODUCTS.values():
        if product_id in category:
            product = deepcopy(category[product_id])
            session.setdefault("cart", []).append(product)
            return product
    return None
