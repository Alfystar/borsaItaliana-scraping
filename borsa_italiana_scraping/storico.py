"""Funzioni per dati storici OHLCV (JSON API grafici.borsaitaliana.it)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from .eccezioni import DatiNonDisponibili, StrumentoNonTrovato
from .sessione import Sessione
from .tipi import PuntoStorico, StoricoRisultato

# Periodi ammessi
_PERIODI_VALIDI = {"1M", "3M", "6M", "1Y", "3Y", "5Y", "MAX"}

# URL base API storico
_URL_STORICO = (
    "https://grafici.borsaitaliana.it/api/instruments/"
    "{isin},XMIL,ISIN/history/period"
)


def _parsa_data(dt_str: str) -> date:
    """Converte una stringa YYYYMMDD in date."""
    return datetime.strptime(dt_str, "%Y%m%d").date()


def _dec(valore: float | int | None) -> Decimal:
    """Converte un numero JSON in Decimal."""
    if valore is None:
        return Decimal("0")
    return Decimal(str(valore))


def _parsa_punto(raw: dict) -> PuntoStorico:
    """Trasforma un elemento historyDt in PuntoStorico."""
    # numero_contratti e controvalore possono mancare nell'ultimo punto
    numero_contratti = raw.get("volNbTrade")
    controvalore = raw.get("volCap")

    return PuntoStorico(
        data=_parsa_data(raw["dt"]),
        apertura=_dec(raw.get("openPx")),
        chiusura=_dec(raw.get("closePx")),
        massimo=_dec(raw.get("highPx")),
        minimo=_dec(raw.get("lowPx")),
        ultimo=_dec(raw.get("lastPx")),
        volume=int(raw.get("qty", 0)),
        numero_contratti=int(numero_contratti) if numero_contratti is not None else None,
        controvalore=_dec(controvalore) if controvalore is not None else None,
    )


def ottieni_storico(
    isin: str,
    periodo: str = "1Y",
    aggiustato: bool = True,
    includi_ultimo: bool = True,
    sessione: Sessione | None = None,
) -> StoricoRisultato:
    """Scarica i dati storici OHLCV per un titolo identificato da ISIN.

    Args:
        isin: codice ISIN dello strumento (es. ``"IT0003128367"``).
        periodo: finestra temporale — ``1M``, ``3M``, ``6M``, ``1Y``, ``3Y``, ``5Y``, ``MAX``.
        aggiustato: se ``True`` applica l'aggiustamento corporate-action.
        includi_ultimo: se ``True`` aggiunge l'ultimo prezzo disponibile.
        sessione: sessione HTTP riutilizzabile (ne viene creata una se ``None``).

    Returns:
        ``StoricoRisultato`` con la lista di ``PuntoStorico``.

    Raises:
        ValueError: se il periodo non è valido.
        StrumentoNonTrovato: se l'ISIN non è riconosciuto.
        DatiNonDisponibili: se la risposta non contiene dati.
    """
    periodo = periodo.upper()
    if periodo not in _PERIODI_VALIDI:
        raise ValueError(
            f"Periodo '{periodo}' non valido. Usa uno tra: {', '.join(sorted(_PERIODI_VALIDI))}"
        )

    isin = isin.strip().upper()

    sessione_locale = sessione is None
    if sessione_locale:
        sessione = Sessione()

    try:
        url = _URL_STORICO.format(isin=isin)
        parametri: dict[str, str] = {"period": periodo}
        if aggiustato:
            parametri["adjustment"] = "true"
        if includi_ultimo:
            parametri["add-last-price"] = "true"

        dati = sessione.get_json(url, params=parametri)

        # Verifica presenza dati
        transco = dati.get("transco", {})
        history = dati.get("history", {})
        punti_raw = history.get("historyDt")

        if not transco or not transco.get("code"):
            raise StrumentoNonTrovato(
                f"ISIN '{isin}' non riconosciuto dall'API di Borsa Italiana"
            )

        if punti_raw is None or len(punti_raw) == 0:
            raise DatiNonDisponibili(
                f"Nessun dato storico disponibile per '{isin}' nel periodo '{periodo}'"
            )

        codice_borsa = transco.get("exchCode", "XMIL")
        punti = [_parsa_punto(p) for p in punti_raw]

        return StoricoRisultato(
            isin=transco.get("code", isin),
            codice_borsa=codice_borsa,
            punti=punti,
        )

    finally:
        if sessione_locale:
            sessione.chiudi()
