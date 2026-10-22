
import os
import ipaddress
from datetime import datetime, timezone

import requests
from flask import Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)

# Render работает перед Flask как прокси.
# Доверяем одному прокси при определении IP клиента.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

# Секретная ссылка будет храниться в настройках Render
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")


def get_location(ip):
    # Проверяем, является ли IP публичным
    try:
        address = ipaddress.ip_address(ip)
        if not address.is_global:
            return {}
    except ValueError:
        return {}

    try:
        response = requests.get(
            f"https://ipwho.is/{ip}",
            timeout=5
        )
        response.raise_for_status()

        data = response.json()

        if data.get("success"):
            return data

    except requests.RequestException as error:
        print("Ошибка геолокации:", error)
    except ValueError:
        print("Сервис вернул некорректный JSON")

    return {}


def send_to_discord(ip, data):
    if not WEBHOOK_URL:
        print("DISCORD_WEBHOOK не настроен")
        return

    connection = data.get("connection") or {}
    location_timezone = data.get("timezone") or {}

    def value(item):
        if item is None or item == "":
            return "Неизвестно"
        return str(item)

    latitude = data.get("latitude")
    longitude = data.get("longitude")

    maps_url = "Недоступна"

    if isinstance(latitude, (int, float)) and isinstance(
        longitude, (int, float)
    ):
        maps_url = (
            f"https://www.google.com/maps"
            f"?q={latitude},{longitude}"
        )

    fields = [
        ("IP", ip),
        ("Тип IP", data.get("type")),
        ("Континент", data.get("continent")),
        ("Страна", data.get("country")),
        ("Код страны", data.get("country_code")),
        ("Регион", data.get("region")),
        ("Город", data.get("city")),
        ("Почтовая зона", data.get("postal")),
        ("Широта", latitude),
        ("Долгота", longitude),
        ("Провайдер", connection.get("isp")),
        ("Организация", connection.get("org")),
        ("ASN", connection.get("asn")),
        ("Домен сети", connection.get("domain")),
        ("Часовой пояс", location_timezone.get("id")),
        ("UTC", location_timezone.get("utc")),
        ("Время визита", datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S UTC")),
    ]

    description = "\n".join(
        f"**{name}:** {value(item)}"
        for name, item in fields
    )

    description += (
        f"\n\n**Google Maps:** {maps_url}"
        "\n_Геолокация приблизительная._"
    )

    payload = {
        "username": "SIGNAL Monitor",
        "allowed_mentions": {"parse": []},
        "embeds": [
            {
                "title": "🌐 Новый посетитель",
                "description": description[:4096],
                "color": 5764768,
            }
        ],
    }

    try:
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            timeout=8
        )
        response.raise_for_status()
        print("Отчёт отправлен в Discord")

    except requests.RequestException as error:
        print("Ошибка отправки в Discord:", error)


@app.route("/")
def home():
    ip = request.remote_addr or "Unknown"

    print("Новый посетитель:", ip)

    location = get_location(ip)
    send_to_discord(ip, location)

    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport"
              content="width=device-width, initial-scale=1">

        <title>SIGNAL</title>

        <style>
            body {
                background: #080d0c;
                color: #52f0a0;
                font-family: Consolas, monospace;
                min-height: 100vh;
                margin: 0;
                display: flex;
                justify-content: center;
                align-items: center;
            }

            .terminal {
                width: min(90%, 850px);
                border: 1px solid #225c43;
                border-radius: 12px;
                padding: 25px;
                background: #101914;
                box-shadow: 0 0 50px #103d2480;
                text-align: center;
            }

            pre {
                color: #52f0a0;
                font-size: clamp(5px, 1.4vw, 13px);
                overflow-x: auto;
                text-align: center;
            }

            h1 {
                color: white;
                letter-spacing: 3px;
            }

            p {
                color: #80ab94;
            }

            .online {
                text-align: left;
                border-bottom: 1px solid #225c43;
                padding-bottom: 15px;
            }

            .footer {
                font-size: 11px;
                margin-top: 35px;
                opacity: 0.65;
            }
        </style>
    </head>

    <body>
        <div class="terminal">
            <div class="online">
                ● SIGNAL.EXE — ONLINE
            </div>

            <pre>
  ____ ___ ____ _   _    _    _
 / ___|_ _/ ___| \\ | |  / \\  | |
 \\___ \\| | |  _|  \\| | / _ \\ | |
  ___) | | |_| | |\\  |/ ___ \\| |___
 |____/___\\____|_| \\_/_/   \\_\\_____|
            </pre>

            <h1>CONNECTION ESTABLISHED</h1>
            <p>Welcome to the other side.</p>

            <p class="footer">
                ACCESS GRANTED // SYSTEM ONLINE
            </p>

            <p class="footer">
                Сайт получает IP посетителя, определяет
                приблизительный регион через ipwho.is
                и отправляет сведения владельцу в Discord.
            </p>
        </div>
    </body>
    </html>
    """
