def parse_cm(text: str) -> float | None:
    s = text.replace(",", ".").strip()
    if not s:
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    if v <= 0 or v > 250:
        return None
    return round(v + 1e-9, 1)


def parse_wrist(text: str) -> float | None:
    s = text.replace(",", ".").strip()
    if not s:
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    if v < 12 or v > 28:
        return None
    return round(v + 1e-9, 1)
