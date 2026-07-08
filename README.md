# 🎬 Vorverkauf-Monitor – Helmstedter Kinos

Überwacht automatisch **3× täglich** (7, 13 und 19 Uhr deutscher Sommerzeit), ob der
Vorverkauf für diese Filme in den Helmstedter Kinos (Roxy Lichtspiele & Camera am
Holzberg) begonnen hat:

- **Spider-Man: Brand New Day**
- **The Odyssey (Die Odyssee)**

## Wie es funktioniert

Die Website [helmstedterkinos.com/programm-01.php](https://www.helmstedterkinos.com/programm-01.php)
bindet ihr Programm über das Ticketsystem **kinoheld.de** ein. Der Monitor fragt
deshalb direkt die Kinoheld-API ab – dort erscheinen Vorstellungen genau in dem
Moment, in dem sie buchbar werden (= Vorverkaufsstart). Das ist zuverlässiger als
das Auslesen der Website selbst, deren Programm nur per JavaScript nachgeladen wird.

| Komponente | Aufgabe |
|---|---|
| `check_presale.py` | Fragt beide Kinos ab (120 Tage Vorschau) und erkennt die Filme |
| `.github/workflows/presale-check.yml` | Führt den Check 3× täglich aus (GitHub Actions) |
| `docs/index.html` | Web-Dashboard mit Live-Status (wird auf den Branch `gh-pages` veröffentlicht) |
| `docs/status.json` / `docs/history.json` | Aktueller Status und Prüfverlauf |

## Benachrichtigung 🔔

Sobald ein Film erstmals buchbar ist, erstellt der Workflow automatisch ein
**GitHub Issue** in diesem Repository (mit @-Erwähnung) – dadurch bekommst du
eine E-Mail von GitHub. Jeder Film wird nur einmal gemeldet.

## Dashboard 📊

**https://emilalexanderreimer-eng.github.io/Kino/**

GitHub Pages ist bereits eingerichtet (Quelle: Branch `gh-pages`). Der Monitor
veröffentlicht das Dashboard nach jedem Prüflauf automatisch dorthin –
es ist keine weitere Einrichtung nötig.

## Manuell prüfen

- Auf GitHub: *Actions → „Vorverkauf-Check“ → Run workflow*
- Lokal: `python3 check_presale.py` (benötigt nur Python 3, keine Abhängigkeiten)

## Filme anpassen

Neue Filme lassen sich in `check_presale.py` in der Liste `MOVIES` ergänzen
(Anzeigename + Erkennungsregel auf den normalisierten Titel).

*Hinweis: GitHub führt geplante Workflows in Repos ohne Aktivität nach ~60 Tagen
automatisch nicht mehr aus – da dieser Workflow bei jedem Lauf den Status committet,
bleibt er dauerhaft aktiv.*
