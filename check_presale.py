#!/usr/bin/env python3
"""Prüft, ob der Vorverkauf für bestimmte Filme in den Helmstedter Kinos begonnen hat.

Die Website https://www.helmstedterkinos.com/programm-01.php bindet ihr Programm
über das Ticketsystem kinoheld.de ein. Dieses Skript fragt die Kinoheld-GraphQL-API
direkt ab – dort erscheinen Vorstellungen genau dann, wenn sie buchbar sind
(= Vorverkauf gestartet).

Ergebnis wird nach docs/status.json und docs/history.json geschrieben.
Für GitHub Actions werden Outputs (newly_detected) nach $GITHUB_OUTPUT geschrieben.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_URL = "https://graph.kinoheld.de/graphql/v1/query"
CINEMAS = {
    "750": "Roxy Lichtspiele",
    "112": "Camera am Holzberg",
}
LOOKAHEAD_DAYS = 120
HISTORY_LIMIT = 500

DOCS = Path(__file__).resolve().parent / "docs"
STATUS_FILE = DOCS / "status.json"
HISTORY_FILE = DOCS / "history.json"


def normalize(title: str) -> str:
    t = title.lower()
    for ch in "-–—:.!,'\"":
        t = t.replace(ch, " ")
    return " ".join(t.split())


def match_endgame_encore(t: str) -> bool:
    return "avengers" in t and "endgame" in t


def match_doomsday(t: str) -> bool:
    return "avengers" in t and "doomsday" in t


MOVIES = [
    {
        "key": "endgame_encore",
        "label": "Avengers: Endgame Encore",
        "matchers": [match_endgame_encore],
    },
    {
        "key": "doomsday",
        "label": "Avengers: Doomsday",
        "matchers": [match_doomsday],
    },
]


def fetch_shows(cinema_id: str) -> list:
    query = (
        "query { shows(cinemaId: %s, days: %d) { name beginning { timestamp } "
        "movie { title } } }" % (cinema_id, LOOKAHEAD_DAYS)
    )
    req = urllib.request.Request(
        API_URL,
        data=json.dumps({"query": query}).encode(),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Vorverkaufs-Monitor Helmstedter Kinos)",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    if "errors" in data:
        raise RuntimeError(f"GraphQL-Fehler: {data['errors']}")
    return data["data"]["shows"] or []


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return default


def main() -> int:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    previous = load_json(STATUS_FILE, {})
    prev_movies = previous.get("movies", {})

    error = None
    all_shows = []  # (cinema_name, show)
    try:
        for cid, cname in CINEMAS.items():
            for show in fetch_shows(cid):
                all_shows.append((cname, show))
    except Exception as exc:  # Netzwerk-/API-Fehler festhalten statt abstürzen
        error = str(exc)
        print(f"FEHLER beim Abruf: {exc}", file=sys.stderr)

    movies_status = {}
    newly_detected = []

    for movie in MOVIES:
        key = movie["key"]
        matches = []
        if error is None:
            for cname, show in all_shows:
                title = normalize(show["name"] or (show.get("movie") or {}).get("title") or "")
                if any(m(title) for m in movie["matchers"]):
                    ts = show["beginning"]["timestamp"]
                    matches.append({
                        "title": show["name"],
                        "cinema": cname,
                        "timestamp": ts,
                    })
        matches.sort(key=lambda s: s["timestamp"])

        prev = prev_movies.get(key, {})
        found = bool(matches)
        if error is not None:
            # Bei Fehler alten Zustand behalten, damit nichts "verschwindet"
            found = prev.get("found", False)
            matches = prev.get("shows", [])

        first_detected = prev.get("firstDetected")
        if found and not first_detected:
            first_detected = now
        if found and not prev.get("found", False):
            newly_detected.append(movie["label"])

        movies_status[key] = {
            "label": movie["label"],
            "found": found,
            "firstDetected": first_detected,
            "shows": matches[:50],
        }

    status = {
        "lastCheck": now,
        "error": error,
        "cinemas": list(CINEMAS.values()),
        "totalShows": len(all_shows),
        "movies": movies_status,
    }

    DOCS.mkdir(exist_ok=True)
    STATUS_FILE.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n")

    history = load_json(HISTORY_FILE, [])
    history.append({
        "time": now,
        "error": error is not None,
        "totalShows": len(all_shows),
        **{k: v["found"] for k, v in movies_status.items()},
    })
    HISTORY_FILE.write_text(
        json.dumps(history[-HISTORY_LIMIT:], ensure_ascii=False, indent=2) + "\n"
    )

    # Outputs für GitHub Actions
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as f:
            f.write(f"newly_detected={'; '.join(newly_detected)}\n")

    for key, m in movies_status.items():
        state = "VORVERKAUF GESTARTET" if m["found"] else "noch nicht im Vorverkauf"
        print(f"{m['label']}: {state} ({len(m['shows'])} Vorstellungen)")
    if newly_detected:
        print(f"NEU ENTDECKT: {', '.join(newly_detected)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
