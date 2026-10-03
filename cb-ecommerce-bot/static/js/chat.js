(() => {
    "use strict";

    const els = {
        history: document.getElementById("chat-history"),
        anchor: document.getElementById("chat-end-anchor"),
        replies: document.getElementById("quick-replies"),
        inputBar: document.getElementById("text-input-container"),
        input: document.getElementById("text-input"),
        submit: document.getElementById("text-submit"),
        menu: document.getElementById("menu-trigger"),
        status: document.getElementById("connection-status"),
        cart: document.getElementById("cart-indicator"),
        label: document.getElementById("input-label")
    };

    const SESSION_KEY = "rulecart_session_id";
    let sessionId = localStorage.getItem(SESSION_KEY);

    if (!sessionId) {
        sessionId = (crypto.randomUUID ? crypto.randomUUID() : `session-${Date.now()}-${Math.random().toString(16).slice(2)}`);
        localStorage.setItem(SESSION_KEY, sessionId);
    }

    let busy = false;

    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function scrollToEnd() {
        requestAnimationFrame(() => {
            els.anchor.scrollIntoView({ behavior: "smooth", block: "end" });
        });
    }

    function appendMessage(text, role = "bot", error = false) {
        const row = document.createElement("div");
        row.className = `message-row ${role}`;
        const bubble = document.createElement("div");
        bubble.className = `message-bubble${error ? " error-bubble" : ""}`;
        bubble.textContent = text;
        row.appendChild(bubble);
        els.history.insertBefore(row, els.anchor);
        scrollToEnd();
    }

    function addTyping() {
        const row = document.createElement("div");
        row.className = "typing-row";
        row.id = "typing-indicator";
        row.innerHTML = `
            <div class="typing-bubble" aria-label="Bot is typing">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
            </div>`;
        els.history.insertBefore(row, els.anchor);
        scrollToEnd();
    }

    function removeTyping() {
        document.getElementById("typing-indicator")?.remove();
    }

    function delayFor(message) {
        const length = String(message || "").length;
        return Math.min(1200, Math.max(500, 500 + length * 8));
    }

    function setInput(payload) {
        const input = payload.input || {};
        const visible = Boolean(input.visible);

        els.inputBar.classList.toggle("input-hidden", !visible);
        els.input.disabled = !visible;
        els.submit.disabled = !visible;

        if (visible) {
            els.input.type = input.type === "email" ? "email" : "tel";
            els.input.inputMode = input.type === "email" ? "email" : "tel";
            els.input.placeholder = input.placeholder || "";
            els.label.textContent = input.type === "email" ? "Email address" : "Phone number";
            setTimeout(() => els.input.focus(), 50);
        } else {
            els.input.value = "";
        }
    }

    function lockHistoricReplies() {
        els.replies.querySelectorAll("button").forEach(button => {
            button.disabled = true;
            button.classList.add("btn-locked");
        });
    }

    function renderChoices(choices) {
        els.replies.replaceChildren();

        (choices || []).forEach(choice => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "quick-reply";
            button.textContent = choice.text;
            button.dataset.choiceId = choice.choice_id;
            button.addEventListener("click", () => {
                sendChoice(choice.choice_id, "");
            });
            els.replies.appendChild(button);
        });

        scrollToEnd();
    }

    function renderCarousel(products) {
        if (!Array.isArray(products) || products.length === 0) return;

        const wrap = document.createElement("div");
        wrap.className = "carousel-container";
        wrap.setAttribute("aria-label", "Product carousel");

        products.forEach(product => {
            const card = document.createElement("article");
            card.className = "product-card";
            card.innerHTML = `
                <img class="product-image"
                     src="${escapeHtml(product.image_url)}"
                     alt="${escapeHtml(product.name)}"
                     loading="lazy">
                <div class="product-body">
                    <h3>${escapeHtml(product.name)}</h3>
                    <p>${escapeHtml(product.description)}</p>
                    <span class="product-price">${escapeHtml(product.price)}</span>
                    <button class="product-action" type="button"
                            data-choice-id="${escapeHtml(product.choice_id)}">
                        View Product
                    </button>
                </div>`;
            card.querySelector("button").addEventListener("click", event => {
                sendChoice(event.currentTarget.dataset.choiceId, "");
            });
            wrap.appendChild(card);
        });

        const row = document.createElement("div");
        row.className = "message-row bot";
        row.appendChild(wrap);
        els.history.insertBefore(row, els.anchor);
        scrollToEnd();
    }

    function renderProduct(product) {
        if (!product) return;
        const row = document.createElement("div");
        row.className = "message-row bot";

        const card = document.createElement("article");
        card.className = "product-card";
        card.innerHTML = `
            <img class="product-image" src="${escapeHtml(product.image_url)}" alt="${escapeHtml(product.name)}">
            <div class="product-body">
                <h3>${escapeHtml(product.name)}</h3>
                <p>${escapeHtml(product.description)}</p>
                <span class="product-price">${escapeHtml(product.price)}</span>
            </div>`;
        row.appendChild(card);
        els.history.insertBefore(row, els.anchor);
        scrollToEnd();
    }

    function renderOrder(order) {
        if (!order) return;

        const row = document.createElement("div");
        row.className = "message-row bot";

        const card = document.createElement("div");
        card.className = "order-card";
        card.innerHTML = `
            <strong>Order ${escapeHtml(order.order_id)}</strong>
            <div class="order-meta">Status: ${escapeHtml(order.status)}</div>
            <div class="order-meta">ETA: ${escapeHtml(order.eta)}</div>
            <div class="order-meta">Items: ${escapeHtml((order.items || []).join(", "))}</div>
            <div class="order-meta">Total: ${escapeHtml(order.total)}</div>`;
        row.appendChild(card);
        els.history.insertBefore(row, els.anchor);
        scrollToEnd();
    }

    function renderCart(items) {
        if (!Array.isArray(items) || items.length === 0) return;

        const row = document.createElement("div");
        row.className = "message-row bot";
        const card = document.createElement("div");
        card.className = "cart-card";

        const title = document.createElement("strong");
        title.textContent = "Cart contents";
        card.appendChild(title);

        items.forEach(item => {
            const line = document.createElement("div");
            line.className = "cart-line";
            line.textContent = `${item.name} — ${item.price}`;
            card.appendChild(line);
        });

        row.appendChild(card);
        els.history.insertBefore(row, els.anchor);
        scrollToEnd();
    }

    async function renderPayload(payload) {
        removeTyping();
        if (payload.error) {
            appendMessage(payload.error, "bot", true);
        }

        await new Promise(resolve => setTimeout(resolve, delayFor(payload.message)));

        if (payload.message) appendMessage(payload.message, "bot");
        if (payload.carousel) renderCarousel(payload.carousel);
        if (payload.product) renderProduct(payload.product);
        if (payload.cart) renderCart(payload.cart);
        if (payload.order) renderOrder(payload.order);

        renderChoices(payload.choices || []);
        setInput(payload);

        if (payload.session) {
            els.cart.textContent = `Cart: ${payload.session.cart_count || 0}`;
        }
        els.status.textContent = "Connected";
        scrollToEnd();
    }

    async function fetchState() {
        const response = await fetch(`/api/state?session_id=${encodeURIComponent(sessionId)}`, {
            headers: { "Accept": "application/json" }
        });
        if (!response.ok) throw new Error("Could not load state");
        return response.json();
    }

    async function sendChoice(choiceId, inputValue) {
        if (busy) return;
        busy = true;

        lockHistoricReplies();
        els.submit.classList.add("btn-loading");
        addTyping();

        try {
            const response = await fetch("/api/message", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Accept": "application/json" },
                body: JSON.stringify({
                    session_id: sessionId,
                    choice_id: choiceId,
                    input_value: inputValue
                })
            });

            const payload = await response.json();
            if (!response.ok && !payload.message) {
                throw new Error(payload.error || "Request failed");
            }
            await renderPayload(payload);
        } catch (error) {
            removeTyping();
            appendMessage(error.message || "Unable to contact the server.", "bot", true);
            els.status.textContent = "Offline";
            renderChoices([]);
        } finally {
            busy = false;
            els.submit.classList.remove("btn-loading");
        }
    }

    async function resetToMainMenu() {
        if (busy) return;
        busy = true;

        els.history.innerHTML = '<div id="chat-end-anchor" aria-hidden="true"></div>';
        els.replies.replaceChildren();
        els.input.value = "";
        addTyping();

        try {
            const response = await fetch("/api/reset", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Accept": "application/json" },
                body: JSON.stringify({ session_id: sessionId })
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || "Reset failed");
            await renderPayload(payload);
        } catch (error) {
            removeTyping();
            appendMessage(error.message || "Could not reset the menu.", "bot", true);
        } finally {
            busy = false;
        }
    }

    els.inputBar.addEventListener("submit", event => {
        event.preventDefault();

        if (!els.inputBar.classList.contains("input-hidden")) {
            const value = els.input.value.trim();
            if (!value) {
                appendMessage("Please enter a value before submitting.", "bot", true);
                return;
            }

            const currentInputType = els.input.type === "email" ? "email" : "phone";
            const choiceId = currentInputType === "email" ? "email_submit" : "phone_submit";
            appendMessage(value, "user");
            els.input.value = "";
            sendChoice(choiceId, value);
        }
    });

    els.menu.addEventListener("click", resetToMainMenu);

    (async function boot() {
        try {
            const payload = await fetchState();
            await renderPayload(payload);
        } catch (error) {
            els.status.textContent = "Offline";
            appendMessage("The chatbot server is not available. Start it with: python app.py", "bot", true);
        }
    })();
})();
