"""Ricerca strumenti su Borsa Italiana (endpoint JSON interno).

L'endpoint ``/borsa/searchengine/all/json/search.html`` restituisce
JSON puro senza protezione WAF — non servono header XHR né JWT.
"""

from __future__ import annotations

from .eccezioni import RicercaNonDisponibile
from .sessione import Sessione
from .tipi import RisultatoRicerca

# URL endpoint JSON (scoperto dal JS ``bb.search.js`` → ``bit.init.search``)
_URL_RICERCA = (
    "https://www.borsaitaliana.it/borsa/searchengine/all/json/search.html"
)


def cerca(
    query: str,
    lingua: str = "it",
    solo_strumenti: bool = True,
    sessione: Sessione | None = None,
) -> list[RisultatoRicerca]:
    """Cerca strumenti finanziari su Borsa Italiana.

    Usa l'endpoint JSON interno del motore di ricerca del sito.

    Args:
        query: testo di ricerca (es. ``"BTP"``, ``"ENEL"``).
        lingua: ``"it"`` o ``"en"``.
        solo_strumenti: se ``True`` restituisce solo le quotes,
            ignorando news/pages/documents.
        sessione: sessione HTTP riutilizzabile.

    Returns:
        Lista di ``RisultatoRicerca``.

    Raises:
        RicercaNonDisponibile: se l'endpoint JSON non risponde.
    """
    lingua = lingua.lower()
    if lingua not in ("it", "en"):
        raise ValueError("La lingua deve essere 'it' o 'en'")

    sessione_locale = sessione is None
    if sessione_locale:
        sessione = Sessione()

    try:
        parametri = {"lang": lingua, "q": query}

        try:
            dati = sessione.get_json(_URL_RICERCA, params=parametri)
        except Exception as err:
            raise RicercaNonDisponibile(
                "La ricerca JSON non è disponibile. "
                "Alternativa: usa lista_btp() per ottenere la lista dei BTP "
                f"oppure ottieni_scheda() con un ISIN noto. Errore: {err}"
            ) from err

        quotes = dati.get("quotes", [])

        # exactSymbolMatch → redirect diretto nel browser, per noi è il match esatto
        exact = dati.get("exactSymbolMatch")
        if exact and isinstance(exact, list):
            quotes = exact + quotes

        risultati: list[RisultatoRicerca] = []
        isin_visti: set[str] = set()

        for q in quotes:
            isin = q.get("symbol", "")
            if not isin or isin in isin_visti:
                continue
            isin_visti.add(isin)
            risultati.append(
                RisultatoRicerca(
                    isin=isin,
                    mic=q.get("mic", ""),
                    nome=q.get("title", ""),
                    tipo=q.get("typeLabel", ""),
                    mercato=q.get("mercato", ""),
                    comparto=q.get("comparto") or None,
                    sotto_comparto=q.get("subcomparto") or None,
                )
            )

        return risultati

    finally:
        if sessione_locale:
            sessione.chiudi()
