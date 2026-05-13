"""borsa-italiana-scraping — Libreria Python per dati finanziari da Borsa Italiana.

Esporta tutte le funzioni e i tipi dell'API pubblica.
"""

# Sessione HTTP
from .sessione import Sessione

# Eccezioni
from .eccezioni import (
    BorsaItalianaErrore,
    DatiNonDisponibili,
    ErroreConnessione,
    RateLimitRaggiunto,
    RicercaNonDisponibile,
    StrumentoNonTrovato,
)

# Tipi di dati
from .tipi import (
    IntradayRisultato,
    PrezzoCorrente,
    PuntoIntraday,
    PuntoStorico,
    RisultatoRicerca,
    SchedaStrumento,
    StoricoRisultato,
    StrumentoLista,
)

# Funzioni
from .storico import ottieni_storico
from .tempo_reale import ottieni_intraday, ottieni_prezzo_corrente
from .ricerca import cerca
from .scheda import ottieni_scheda
from .lista import lista_btp

__version__ = "0.1.0"

__all__ = [
    # Sessione
    "Sessione",
    # Eccezioni
    "BorsaItalianaErrore",
    "DatiNonDisponibili",
    "ErroreConnessione",
    "RateLimitRaggiunto",
    "RicercaNonDisponibile",
    "StrumentoNonTrovato",
    # Tipi
    "IntradayRisultato",
    "PrezzoCorrente",
    "PuntoIntraday",
    "PuntoStorico",
    "RisultatoRicerca",
    "SchedaStrumento",
    "StoricoRisultato",
    "StrumentoLista",
    # Funzioni
    "ottieni_storico",
    "ottieni_intraday",
    "ottieni_prezzo_corrente",
    "cerca",
    "ottieni_scheda",
    "lista_btp",
]
