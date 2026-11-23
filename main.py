
import os
import json
import requests

from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo


BASE_URL = "http://127.0.0.1:8000"
STATE_FILE = Path("state.json")

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

TIMEZONE = ZoneInfo("Europe/Warsaw")


def load_state():
    if STATE_FILE.exists():
        try:
            state = json.loads(
                STATE_FILE.read_text(encoding="utf-8")
            )

            state.setdefault("sent", [])
            state.setdefault("initialized", False)

            return state

        except Exception:
            pass

    return {
        "sent": [],
        "initialized": False,
        "last_health_message": None
    }


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def api_get(path, params=None):
    response = requests.get(
        BASE_URL + path,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=20
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(f"Telegram: {result}")


def get_period(periods, search):
    for period in periods or []:
        name = str(
            period.get("period", period.get("name", ""))
        ).lower()

        if search.lower() in name:
            return period

    return None


def score(value):
    try:
        return int(value)

    except (TypeError, ValueError):
        return None


def send_daily_health_message(state):
    now = datetime.now(TIMEZONE)
    today = now.strftime("%Y-%m-%d")

    if now.hour < 21:
        return

    if state.get("last_health_message") == today:
        return

    message = (
        "✅ BOT DZIAŁA PRAWIDŁOWO!\n\n"
        "🤖 Automatyczne sprawdzanie meczów jest aktywne.\n"
        "⚽ Bot szuka goli wyrównujących w drugiej połowie.\n"
        "⏱ Sprawdzanie odbywa się co 5 minut.\n"
        "📅 Wiadomość kontrolna: 21:00"
    )

    try:
        send_telegram(message)

        state["last_health_message"] = today
        save_state(state)

        print("WYSŁANO DZIENNĄ WIADOMOŚĆ KONTROLNĄ.")

    except Exception as error:
        print(
            f"BŁĄD WIADOMOŚCI KONTROLNEJ: {error}"
        )


def scan():
    state = load_state()

    data = api_get(
        "/matches/live",
        {"sport": "football"}
    )

    matches = []

    for competition in data.get("competitions", []):
        comp = competition.get("competition", {})

        league = comp.get(
            "display_name",
            "Nieznana liga"
        )

        country = comp.get(
            "category",
            "Nieznany kraj"
        )

        for match in competition.get("matches", []):
            stage = str(
                match.get("stage", "")
            ).lower()

            if stage == "2nd half":
                matches.append(
                    (match, league, country)
                )

    print(
        f"Mecze w drugiej połowie: {len(matches)}"
    )

    found = []

    for match, league, country in matches:
        match_id = match.get("id")

        home = match.get(
            "home", {}
        ).get("name", "Gospodarze")

        away = match.get(
            "away", {}
        ).get("name", "Goście")

        if not match_id:
            continue

        try:
            summary = api_get(
                "/matches/summary",
                {"match": match_id}
            )

        except Exception as error:
            print(
                f"BŁĄD historii {home} - {away}: {error}"
            )
            continue

        periods = summary.get("periods", [])

        first = get_period(
            periods,
            "1st Half"
        )

        second = get_period(
            periods,
            "2nd Half"
        )

        if not first or not second:
            print(
                f"Brak danych połowy: {home} - {away}"
            )
            continue

        ht_home = score(
            first.get("home_score")
        )

        ht_away = score(
            first.get("away_score")
        )

        if ht_home is None or ht_away is None:
            print(
                f"Brak wyniku do przerwy: {home} - {away}"
            )
            continue

        incidents = second.get("incidents", [])

        print(
            f"{home} - {away}: "
            f"zdarzeń w 2. połowie: {len(incidents)}"
        )

        for incident in incidents:
            incident_type = str(
                incident.get("type", "")
            ).lower()

            if incident_type != "goal":
                continue

            minute = score(
                incident.get("minute_number")
            )

            if minute is None or minute < 46:
                continue

            h = score(
                incident.get("home_score")
            )

            a = score(
                incident.get("away_score")
            )

            if h is None or a is None:
                print(
                    f"Pominięto gola bez wyniku: {match_id}"
                )
                continue

            if h != a:
                print(
                    f"Gol bez wyrównania: "
                    f"{home} - {away}, {minute}'"
                )
                continue

            team = (
                home
                if incident.get("team") == "home"
                else away
            )

            player = incident.get("player") or {}

            scorer = player.get(
                "name",
                "Nieznany"
            )

            incident_id = incident.get("id")

            if incident_id is None:
                incident_id = (
                    f"{minute}-{h}-{a}-{team}"
                )

            event_key = (
                f"{match_id}-{incident_id}"
            )

            if event_key in state["sent"]:
                print(
                    f"Duplikat pominięty: {event_key}"
                )
                continue

            message = (
                "⚽ GOL WYRÓWNUJĄCY!\n"
                f"🌍 {league}\n"
                f"🏳️ {country}\n"
                f"🏆 {home} – {away}\n"
                f"🔥 Wyrównuje: {team}\n"
                f"⏱ {minute}'\n"
                f"👤 Strzelec: {scorer}\n"
                f"📊 Wynik do przerwy: "
                f"{ht_home}:{ht_away}\n"
                f"⚽ Wynik po golu: {h}:{a}"
            )

            found.append(
                (event_key, message)
            )

    print(
        f"\nNowe gole wyrównujące: {len(found)}"
    )

    if not state.get("initialized", False):
        for key, _ in found:
            state["sent"].append(key)

        state["initialized"] = True
        save_state(state)

        print(
            "Pierwsza inicjalizacja zakończona "
            "bez starych alertów."
        )

    else:
        for key, message in found:
            try:
                send_telegram(message)

                state["sent"].append(key)
                save_state(state)

                print(
                    f"WYSŁANO ALERT: {key}"
                )

            except Exception as error:
                print(
                    f"BŁĄD TELEGRAM: {error}"
                )

    send_daily_health_message(state)


if __name__ == "__main__":
    try:
        scan()

    except Exception as error:
        print(
            f"BŁĄD GŁÓWNY: {error}"
        )

        raise
