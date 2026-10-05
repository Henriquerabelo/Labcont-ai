from __future__ import annotations

from datetime import date


def txt(form, campo: str, maiusculo: bool = False) -> str | None:
    v = (form.get(campo) or "").strip()
    if not v:
        return None
    return v.upper() if maiusculo else v


def inteiro(form, campo: str) -> int | None:
    v = (form.get(campo) or "").strip()
    try:
        return int(v) if v else None
    except ValueError:
        return None


def data(form, campo: str) -> date | None:
    v = (form.get(campo) or "").strip()
    try:
        return date.fromisoformat(v) if v else None
    except ValueError:
        return None
