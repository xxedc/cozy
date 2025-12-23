# 🛡️ VPN Bot (Aiogram 3 + Marzban)

A modern, asynchronous Telegram bot for selling and managing VPN subscriptions based on the **VLESS** protocol (via **Marzban** panel). Built with Python 3.10+, Aiogram 3, and SQLAlchemy.

!Python
!Aiogram
!Marzban

[🇷🇺 Русский README](README_RU.md)

## ✨ Features

*   **🛒 Subscription Store:** Buy VPN keys for different durations (1 month to 1 year).
*   **🌍 Multi-Location Support:** Support for multiple servers/countries (e.g., Sweden, Germany).
*   **👤 User Profile:** Balance system, subscription management, traffic usage stats.
*   **🎁 Trial System:** Automatic issuance of 24-hour trial keys.
*   **🎟️ Promo Codes:** System for discounts, balance top-ups, and free days.
*   **👮 Admin Panel:** User management, broadcasting, statistics, and promo code creation.
*   **🌐 I18n:** Multi-language support (English & Russian).
*   **💳 Payment Ready:** Modular structure for integrating payment gateways (CryptoBot, Stripe, etc.).

## 🛠️ Tech Stack

*   **Framework:** Aiogram 3.x
*   **Database:** SQLAlchemy (Async) + PostgreSQL (via Docker) / SQLite
*   **Settings:** Pydantic Settings
*   **Logging:** Loguru
*   **Scheduler:** APScheduler

## 🚀 Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/telegram-vpn-shop.git
    cd telegram-vpn-shop
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    # venv\Scripts\activate   # Windows
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuration:**
    Create a `.env` file in the root directory:
    ```env
    BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
    DB_URL=sqlite+aiosqlite:///bot.db
    ADMIN_IDS=[123456789, 987654321]
    MARZBAN_HOST=https://your-marzban-panel.com
    MARZBAN_USERNAME=admin
    MARZBAN_PASSWORD=password
    ```

5.  **Run the bot:**
    ```bash
    python main.py
    ```

## ⚠️ Note on Marzban API

The current version includes a **Mock API** service (`src/services/marzban_api.py`) for testing purposes without a real server.
To use it in production, you need to implement the actual HTTP requests to your Marzban instance in this file.

## 📄 License

This project is licensed under the MIT License.