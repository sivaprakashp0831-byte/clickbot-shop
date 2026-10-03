"""
Deterministic state-machine-driven e-commerce chatbot.
Run with: python app.py
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request

from database import (
    CATEGORIES,
    PRODUCTS,
    STATE_TREE,
    add_product_to_cart,
    create_order,
    get_or_create_session,
    get_order_for_session,
    save_session,
)

BASE_DIR = Path(__file__).resolve().parent
ANALYTICS_FILE = BASE_DIR / "analytics.json"
ANALYTICS_LOCK = Lock()

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
PHONE_RE = re.compile(r"^\+?[1-9]\d{1,14}$")

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


def write_analytics(current_state: str, choice_clicked: str, drop_off_flag: bool) -> None:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "current_state": current_state,
        "choice_clicked": choice_clicked,
        "drop_off_flag": bool(drop_off_flag),
    }
    with ANALYTICS_LOCK:
        events = []
        if ANALYTICS_FILE.exists():
            try:
                events = json.loads(ANALYTICS_FILE.read_text(encoding="utf-8"))
                if not isinstance(events, list):
                    events = []
            except (json.JSONDecodeError, OSError):
                events = []
        events.append(event)
        ANALYTICS_FILE.write_text(json.dumps(events, indent=2), encoding="utf-8")


def state_payload(session: Dict[str, Any]) -> Dict[str, Any]:
    state = session["state"]
    node = STATE_TREE[state]
    choices = list(node.get("choices", []))

    # The active-order button is injected only when the session has an active order.
    if state == "main_menu":
        has_active_order = bool(get_order_for_session(session["session_id"]))
        choices = [
            choice for choice in choices
            if choice.get("choice_id") != "track_order"
            or has_active_order
        ]

    payload: Dict[str, Any] = {
        "state": state,
        "message": node.get("message", ""),
        "choices": choices,
        "input": {
            "visible": bool(node.get("input_type")),
            "type": node.get("input_type"),
            "placeholder": (
                "you@example.com" if node.get("input_type") == "email"
                else "+919876543210" if node.get("input_type") == "phone"
                else ""
            ),
        },
        "session": {
            "has_active_order": bool(get_order_for_session(session["session_id"])),
            "cart_count": len(session.get("cart", [])),
            "email": session.get("email"),
            "phone": session.get("phone"),
        },
    }

    if state in {"electronics", "apparel", "home"}:
        category = state
        payload["carousel"] = [
            {
                **product,
                "price": f"₹{product['price']:,.2f}",
                "choice_id": next(
                    c["choice_id"] for c in node["choices"]
                    if c["next_state"] == next(
                        ps for ps, item_id in {
                            "product_phone_x1": "phone-x1",
                            "product_headphones_hd": "headphones-hd",
                            "product_watch_fit": "watch-fit",
                            "product_shirt_cotton": "shirt-cotton",
                            "product_hoodie_core": "hoodie-core",
                            "product_sneakers_run": "sneakers-run",
                            "product_lamp_desk": "lamp-desk",
                            "product_bottle_steel": "bottle-steel",
                            "product_organizer_box": "organizer-box",
                        }.items() if item_id == product["id"]
                    )
                )
            }
            for product in PRODUCTS[category].values()
        ]
    elif state.startswith("product_"):
        product_id = node["product_id"]
        product = next(
            product for products in PRODUCTS.values()
            for product in products.values()
            if product["id"] == product_id
        )
        payload["product"] = {**product, "price": f"₹{product['price']:,.2f}"}
    elif state == "cart":
        payload["cart"] = [
            {**item, "price": f"₹{item['price']:,.2f}"}
            for item in session.get("cart", [])
        ]
    elif state in {"checkout_confirm", "order_created", "order_status"}:
        order = get_order_for_session(session["session_id"])
        if order:
            payload["order"] = {**order, "total": f"₹{order['total']:,.2f}"}
        else:
            payload["order"] = None

    return payload


def error_payload(session: Dict[str, Any], message: str, input_type: str) -> Dict[str, Any]:
    payload = state_payload(session)
    payload["error"] = message
    payload["input"] = {
        "visible": True,
        "type": input_type,
        "placeholder": "you@example.com" if input_type == "email" else "+919876543210",
    }
    return payload


def process_choice(session: Dict[str, Any], choice_id: str, input_value: str) -> Dict[str, Any]:
    current_state = session["state"]
    node = STATE_TREE[current_state]
    choice = next((c for c in node.get("choices", []) if c["choice_id"] == choice_id), None)

    # Typed form submissions are validated against the active node.
    input_type = node.get("input_type")
    if input_type:
        value = (input_value or "").strip()
        if input_type == "email":
            if not EMAIL_RE.fullmatch(value):
                write_analytics(current_state, choice_id or "invalid_email", True)
                return error_payload(session, "Invalid email. Please enter a valid email address.", "email")
            session["email"] = value
        elif input_type == "phone":
            if not PHONE_RE.fullmatch(value):
                write_analytics(current_state, choice_id or "invalid_phone", True)
                return error_payload(session, "Invalid phone number. Use international format, e.g. +919876543210.", "phone")
            session["phone"] = value

    if choice is None:
        write_analytics(current_state, choice_id or "unknown_choice", True)
        return error_payload(session, "That action is not available in the current state. Please choose one of the visible options.", input_type or "text")

    if choice.get("requires_active_order") and not get_order_for_session(session["session_id"]):
        write_analytics(current_state, choice_id, True)
        return error_payload(session, "There is no active order for this session.", "text")

    next_state = choice["next_state"]

    # Deterministic product actions.
    if choice_id.startswith("add_"):
        product_id = choice_id.removeprefix("add_").replace("_", "-")
        if product_id in {p["id"] for category in PRODUCTS.values() for p in category.values()}:
            add_product_to_cart(session, product_id)

    if next_state == "checkout" and not session.get("cart"):
        # A deterministic fallback cart keeps the demo checkout executable.
        add_product_to_cart(session, "phone-x1")

    if next_state == "order_created":
        if not session.get("email") or not session.get("phone"):
            session["state"] = "checkout_email"
        else:
            create_order(session)
            session["state"] = "order_created"
    else:
        session["state"] = next_state

    save_session(session)

    # Drop-off is recorded for explicit exits to the main menu from non-main states.
    drop_off = current_state != "main_menu" and next_state == "main_menu"
    write_analytics(current_state, choice_id, drop_off)
    return state_payload(session)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/state")
def get_state():
    session_id = request.args.get("session_id", "").strip()
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    session = get_or_create_session(session_id)
    return jsonify(state_payload(session))


@app.post("/api/message")
def message():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    choice_id = data.get("choice_id")
    input_value = data.get("input_value", "")

    if not isinstance(session_id, str) or not session_id.strip():
        return jsonify({"error": "session_id must be a non-empty string"}), 400
    if not isinstance(choice_id, str) or not choice_id.strip():
        return jsonify({"error": "choice_id must be a non-empty string"}), 400
    if not isinstance(input_value, str):
        return jsonify({"error": "input_value must be a string"}), 400

    session = get_or_create_session(session_id.strip())
    try:
        payload = process_choice(session, choice_id.strip(), input_value)
        return jsonify(payload)
    except Exception:
        write_analytics(session["state"], choice_id.strip(), True)
        return jsonify({
            "state": session["state"],
            "message": "A deterministic server error occurred. Please return to the Main Menu.",
            "choices": [{"choice_id": "server_reset", "text": "⏮️ Main Menu", "next_state": "main_menu"}],
            "input": {"visible": False, "type": None, "placeholder": ""},
            "error": "Request could not be completed.",
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)


@app.post("/api/reset")
def reset():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        return jsonify({"error": "session_id must be a non-empty string"}), 400
    session = get_or_create_session(session_id.strip())
    session["state"] = "main_menu"
    session["cart"] = []
    save_session(session)
    write_analytics("main_menu", "menu_reset", False)
    return jsonify(state_payload(session))


if __name__ == "__main__":
    if not ANALYTICS_FILE.exists():
        ANALYTICS_FILE.write_text("[]", encoding="utf-8")
    app.run(host="127.0.0.1", port=5000, debug=False)
