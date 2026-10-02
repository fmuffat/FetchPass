"""
FetchPass - Ticket Translations
Labels used on the printed ticket and the on-screen preview.
"""

TEXT = {
    "en": {"network": "Network",  "password": "Password",     "valid": "Valid for",
           "created": "Created",  "expires":  "Expires",
           "h": "h", "day(s)": "day(s)",  "week(s)": "week(s)"},
    "fr": {"network": "Réseau",   "password": "Mot de passe", "valid": "Validité",
           "created": "Créé le",  "expires":  "Expire le",
           "h": "h", "day(s)": "jour(s)", "week(s)": "semaine(s)"},
    "de": {"network": "Netzwerk", "password": "Passwort",     "valid": "Gültig",
           "created": "Erstellt", "expires":  "Läuft ab",
           "h": "Std.", "day(s)": "Tag(e)", "week(s)": "Woche(n)"},
    "it": {"network": "Rete",     "password": "Password",     "valid": "Validità",
           "created": "Creato",   "expires":  "Scade",
           "h": "h", "day(s)": "giorno/i", "week(s)": "settimana/e"},
}


def ticket_fields(voucher: dict, language: str) -> list:
    """Return [(label, value), ...] in ticket order, labels padded to equal width."""
    t = TEXT.get(language, TEXT["en"])

    # Clients format durations as "<n> <unit>" with English unit labels
    duration = voucher.get("duration", "")
    value, _, unit = duration.partition(" ")
    if unit in t:
        duration = f"{value} {t[unit]}"

    fields = [
        ("network",  voucher.get("ssid", "")),
        ("password", voucher.get("key", "")),
        ("valid",    duration),
        ("created",  voucher.get("created", "")),
        ("expires",  voucher.get("expires", "")),
    ]
    width = max(len(t[k]) for k, _ in fields)
    return [(t[k].ljust(width), v) for k, v in fields]
