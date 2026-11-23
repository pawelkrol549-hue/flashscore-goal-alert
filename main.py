
import os
import json
import time
import requests
from pathlib import Path

BASE_URL = "http://localhost:8000"
STATE_FILE = Path("state.json")
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"sent": [], "initialized": False}


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    response = requests.post(
        url,
        json={"chat_id": TELEGRAM_CHAT_ID, "text": message},
        timeout=20
    )
    response.raise_for_status()


def get_json(path, params=None):
    response = requests.get(
        f"{BASE_URL}{path}",
        params=params,
        timeout=30
    )
    response.raise_for_status()
    return response.json()


def get_period(periods, name):
    for period in periods or []:
        if name.lower() in str(period.get("name", "")).lower():
            return period
    return None


def scan_matches(state):
    data = get_json("/matches/live", {"sport": "football"})
    matches = []

    for competition in data.get("competitions", []):
        league = competition.get("competition", {}).get("display_name", "Nieznane rozgrywki")
        country = competition.get("competition", {}).get("category", "Nieznany kraj")

        for match in competition.get("matches", []):
            if match.get("stage") == "2nd Half":
                matches.append((match, league, country))

    print(f"Znaleziono meczów w drugiej połowie: {len(matches)}")

    found_goals = []

    for match, league, country in matches:
        match_id = match.get("id")
        if not match_id:
            continue

        try:
            summary = get_json("/matches/summary", {"match": match_id})
        except Exception as error:
            print(f"Nie udało się pobrać meczu {match_id}: {error}")
            continue

        periods = summary.get("periods", [])
        first_half = get_period(periods, "1st Half")
        second_half = get_period(periods, "2nd Half")

        if not first_half or not second_half:
            continue

        ht_home = first_half.get("home_score")
        ht_away = first_half.get("away_score")

        if ht_home is None or ht_away is None:
            continue

        for incident in second_half.get("incidents", []):
            if str(incident.get("type", "")).lower() != "goal":
                continue

            minute = incident.get("minute_number")
            if minute is None or int(minute) < 46:
                continue

            home_score = incident.get("home_score")
            away_score = incident.get("away_score")

            if home_score is None or away_score is None:
                continue

            if int(home_score) != int(away_score):
                continue

            incident_id = incident.get("id")
            if incident_id is None:
                incident_id = (
                    f"{match_id}-{minute}-{home_score}-{away_score}-"
                    f"{incident.get('team')}"
                )

            event_key = f"{match_id}-{incident_id}"

            if event_key in state["sent"]:
                continue

            home_name = match.get("home", {}).get("name", "Gospodarze")
            away_name = match.get("away", {}).get("name", "Goście")
            scoring_team = (
                home_name if incident.get("team") == "home" else away_name
            )
            scorer = incident.get("player", {}).get("name", "Nieznany")

            message = (
                "⚽ GOL WYRÓWNUJĄCY!\n"
                f"🌍 {league}\n"
                f"🏳️ {country}\n"
                f"🏆 {home_name} – {away_name}\n"
                f"🔥 Wyrównuje: {scoring_team}\n"
                f"⏱ {minute}'\n"
                f"👤 Strzelec: {scorer}\n"
                f"📊 Wynik do przerwy: {ht_home}:{ht_away}\n"
                f"⚽ Wynik po golu: {home_score}:{away_score}"
            )

            found_goals.append((event_key, message))

    if not state["initialized"]:
        for event_key, _ in found_goals:
            state["sent"].append(event_key)
        state["initialized"] = True
        save_state(state)
        print("Pierwsze uruchomienie: zapisano istniejące gole bez wysyłania alertów.")
        return

    for event_key, message in found_goals:
        try:
            send_telegram(message)
            state["sent"].append(event_key)
            save_state(state)
            print(f"Wysłano alert: {event_key}")
        except Exception as error:
            print(f"Błąd wysyłania alertu: {error}")


if __name__ == "__main__":
    state = load_state()
    scan_matches(state)
