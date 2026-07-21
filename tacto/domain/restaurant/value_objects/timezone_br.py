"""
Brazilian state (UF) → IANA timezone mapping.

Pure domain helper. Brazil abolished daylight saving time in 2019, so the
offsets below are currently fixed, but the IANA zones handle historical and
future transitions correctly via ZoneInfo.
"""

from __future__ import annotations

from typing import Optional

# One canonical IANA timezone per Brazilian state.
# UTC-3: America/Sao_Paulo (and regional equivalents), UTC-4: Cuiaba/Manaus/etc,
# UTC-5: Rio_Branco.
BR_UF_TIMEZONES: dict[str, str] = {
    "AC": "America/Rio_Branco",
    "AL": "America/Maceio",
    "AP": "America/Belem",
    "AM": "America/Manaus",
    "BA": "America/Bahia",
    "CE": "America/Fortaleza",
    "DF": "America/Sao_Paulo",
    "ES": "America/Sao_Paulo",
    "GO": "America/Sao_Paulo",
    "MA": "America/Fortaleza",
    "MT": "America/Cuiaba",
    "MS": "America/Campo_Grande",
    "MG": "America/Sao_Paulo",
    "PA": "America/Belem",
    "PB": "America/Fortaleza",
    "PR": "America/Sao_Paulo",
    "PE": "America/Recife",
    "PI": "America/Fortaleza",
    "RJ": "America/Sao_Paulo",
    "RN": "America/Fortaleza",
    "RS": "America/Sao_Paulo",
    "RO": "America/Porto_Velho",
    "RR": "America/Boa_Vista",
    "SC": "America/Sao_Paulo",
    "SP": "America/Sao_Paulo",
    "SE": "America/Maceio",
    "TO": "America/Araguaina",
}


def timezone_for_uf(uf: Optional[str]) -> Optional[str]:
    """Return the IANA timezone for a Brazilian state code (UF).

    Returns None when the UF is empty or unknown, so the caller can fall back
    to its own default timezone.
    """
    if not uf:
        return None
    return BR_UF_TIMEZONES.get(uf.strip().upper())
