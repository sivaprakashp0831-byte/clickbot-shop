# RuleCart — Deterministic E-Commerce Chatbot

## Run
1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Run `python -m pip install -r requirements.txt`.
4. Run `python app.py`.
5. Open http://127.0.0.1:5000/

## Design
- Flask backend
- Explicit state-machine routing
- Static mock product/order data
- Regex validation for email and phone
- Server-side in-memory sessions keyed by a browser-generated session ID
- JSON analytics log in `analytics.json`
- Vanilla HTML/CSS/JavaScript frontend
- No trained models, NLP libraries, LLMs, OpenAI APIs, or AI services

## Demo active order
A simulated active order exists for session ID `demo-active-session`. The normal browser creates its own session ID, so its Main Menu starts without Track Order until an order is created.

## Important
Product image URLs are remote Unsplash image URLs. The application itself contains no AI dependency.
