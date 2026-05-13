"""Tipi di dati (dataclass) per i risultati della libreria."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


# ---------------------------------------------------------------------------
# Storico
# ---------------------------------------------------------------------------

@dataclass
class PuntoStorico:
    """Singolo punto OHLCV giornaliero."""
    data: date
    apertura: Decimal
    chiusura: Decimal
    massimo: Decimal
    minimo: Decimal
    ultimo: Decimal
    volume: int
    numero_contratti: int | None = None
    controvalore: Decimal | None = None


@dataclass
class StoricoRisultato:
    """Risultato della query storica per uno strumento."""
    isin: str
    codice_borsa: str  # es. "XMIL"
    punti: list[PuntoStorico] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Intraday / prezzo corrente
# ---------------------------------------------------------------------------

@dataclass
class PuntoIntraday:
    """Singola candela intraday."""
    orario: datetime
    apertura: Decimal
    chiusura: Decimal
    massimo: Decimal
    minimo: Decimal
    volume: int
    numero_contratti: int
    controvalore: Decimal
    chiusura_precedente: Decimal | None = None


@dataclass
class IntradayRisultato:
    """Risultato della query intraday."""
    isin: str
    punti: list[PuntoIntraday] = field(default_factory=list)


@dataclass
class PrezzoCorrente:
    """Prezzo corrente (o più recente) di uno strumento."""
    isin: str
    prezzo: Decimal
    variazione_percentuale: Decimal | None
    data: date
    valuta: str
    fonte: str  # "api" o "scraping"


# ---------------------------------------------------------------------------
# Ricerca
# ---------------------------------------------------------------------------

@dataclass
class RisultatoRicerca:
    """Singolo risultato dalla ricerca strumenti."""
    isin: str
    mic: str
    nome: str
    tipo: str  # "Obbligazione", "Azione", ecc.
    mercato: str
    comparto: str | None = None
    sotto_comparto: str | None = None


# ---------------------------------------------------------------------------
# Scheda strumento
# ---------------------------------------------------------------------------

@dataclass
class SchedaStrumento:
    """Dati estratti dalla pagina scheda di uno strumento."""
    isin: str
    nome: str
    prezzo: Decimal
    variazione_percentuale: Decimal | None
    valuta: str
    tipo: str  # "azione", "obbligazione", "etf", "altro"
    mercato: str

    # --- Campi specifici obbligazioni (None per azioni) ---
    rendimento_lordo: Decimal | None = None
    rendimento_netto: Decimal | None = None
    rateo_lordo: Decimal | None = None
    rateo_netto: Decimal | None = None
    duration_modificata: Decimal | None = None
    cedola_annua: Decimal | None = None
    cedola_periodale: Decimal | None = None
    scadenza: date | None = None
    emittente: str | None = None
    tipo_bond: str | None = None
    lotto_minimo: int | None = None
    descrizione_payout: str | None = None

    # --- Campi specifici azioni (None per obbligazioni) ---
    settore: str | None = None
    capitalizzazione: Decimal | None = None
    ticker: str | None = None
    performance_1m: Decimal | None = None
    performance_6m: Decimal | None = None
    performance_1y: Decimal | None = None


# ---------------------------------------------------------------------------
# Lista strumenti
# ---------------------------------------------------------------------------

@dataclass
class StrumentoLista:
    """Strumento da una lista HTML (es. lista BTP)."""
    isin: str
    nome: str
    ultimo_prezzo: Decimal | None
    cedola: Decimal | None
    scadenza: date | None
    mic: str
