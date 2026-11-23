
import requests
import json
from datetime import datetime, timezone

FLASHscore_URL = "http://localhost:8000/matches/live"

def get_live_matches():
    try:
        response = requests.get(FLASHscore_URL, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception as error:
        print("Błąd pobierania:", error)
        return None

def main():
    print("=== FLASHscore GOAL ALERT ===")
    print("Czas:", datetime.now(timezone.utc))

    matches = get_live_matches()

    if matches is None:
        print("Nie udało się pobrać meczów.")
        return

    print(json.dumps(matches, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
