
import os
import json
import requests
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        },
        timeout=20
    )
    response.raise_for_status()

def is_equalizer(match):
    """
    Sprawdza, czy gol w drugiej połowie
    doprowadził do remisu.
    """
    minute = match.get("minute")
    halftime = match.get("halftime")
    home = match.get("home_score")
    away = match.get("away_score")
    scoring_team = match.get("scoring_team")
    league = match.get("league", "Nieznana liga")
    home_name = match.get("home_team", "Gospodarze")
    away_name = match.get("away_team", "Goście")

    if not all(value is not None for value in [
        minute, halftime, home, away, scoring_team
    ]):
        return None

    if minute < 46 or minute > 130:
        return None

    if home != away:
        return None

    if halftime[0] == halftime[1]:
        return None

    message = (
        "⚽ GOL WYRÓWNUJĄCY!\n\n"
        f"🏆 Liga: {league}\n"
        f"⚔️ Mecz: {home_name} - {away_name}\n"
        f"🔥 Strzela: {scoring_team}\n"
        f"⏱️ Minuta: {minute}'\n"
        f"📊 Do przerwy: {halftime[0]}:{halftime[1]}\n"
        f"🟢 Aktualny wynik: {home}:{away}"
    )

    return message

def main():
    print("=== GOAL ALERT ===")
    print("Czas:", datetime.now(timezone.utc))

    # Test mechanizmu na przykładowym meczu.
    test_match = {
        "minute": 67,
        "halftime": [0, 1],
        "home_score": 1,
        "away_score": 1,
        "home_team": "Drużyna A",
        "away_team": "Drużyna B",
        "scoring_team": "Drużyna A",
        "league": "Liga testowa"
    }

    message = is_equalizer(test_match)

    if message:
        print(message)
        send_telegram(message)
        print("Wysłano testowy alert!")
    else:
        print("Brak gola wyrównującego.")

if __name__ == "__main__":
    main()
