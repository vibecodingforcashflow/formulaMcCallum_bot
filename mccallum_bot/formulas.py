from dataclasses import dataclass
from typing import Literal

MeasurementKey = Literal[
    "chest", "waist", "thigh", "neck", "biceps", "calf", "forearm"
]


@dataclass(frozen=True)
class IdealSet:
    wrist: float
    chest: float
    waist: float
    thigh: float
    neck: float
    biceps: float
    calf: float
    forearm: float


def round_cm(x: float) -> float:
    return round(x + 1e-9, 1)


def ideals_from_wrist(wrist_cm: float) -> IdealSet:
    w = wrist_cm
    c = 6.5 * w
    return IdealSet(
        wrist=round_cm(w),
        chest=round_cm(c),
        waist=round_cm(0.70 * c),
        thigh=round_cm(0.53 * c),
        neck=round_cm(0.37 * c),
        biceps=round_cm(0.36 * c),
        calf=round_cm(0.34 * c),
        forearm=round_cm(0.29 * c),
    )


def pct_of_ideal(actual: float, ideal: float) -> float:
    if ideal <= 0:
        return 0.0
    return round(100.0 * actual / ideal, 1)


def color_class(key: MeasurementKey, actual: float, ideal: float) -> str:
    """good = green, bad = red (CSS class names)."""
    if key == "waist":
        if actual <= ideal:
            return "good"
        return "bad"
    if actual >= ideal:
        return "good"
    return "bad"


ORDER: list[MeasurementKey] = [
    "chest",
    "waist",
    "thigh",
    "neck",
    "biceps",
    "calf",
    "forearm",
]

LABEL_RU: dict[MeasurementKey, str] = {
    "chest": "Грудь",
    "waist": "Талия",
    "thigh": "Бедро",
    "neck": "Шея",
    "biceps": "Бицепс",
    "calf": "Голень",
    "forearm": "Предплечье",
}
