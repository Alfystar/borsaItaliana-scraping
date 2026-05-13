"""Ricerca strumenti su Borsa Italiana (endpoint JSON XHR)."""

from __future__ import annotations

from .eccezioni import RicercaNonDisponibile
from .sessione import Sessione
from .tipi import RisultatoRicerca

# URL endpoint ricerca
_URL_RICERCA = "https://www.borsaitaliana.it/borsa/searchengine/search.html"


def cerca(
    query: str,
    lingua: str = "it",
    solo_strumenti: bool = True,
    sessione: Sessione | None = None,
) -> list[RisultatoRicerca]:
    """Cerca strumenti finanziari su Borsa Italiana.

    Usa l'endpoint JSON XHR del motore di ricerca del sito.

    Args:
        query: testo di ricerca (es. ``"BTP"``, ``"ENEL"``).
        lingua: ``"it"`` o ``"en"``.
        solo_strumenti: se ``True`` restituisce solo le quotes,
            ignorando news/pages/documents.
        sessione: sessione HTTP riutilizzabile.

    Returns:
        Lista di ``RisultatoRicerca``.

    Raises:
        RicercaNonDisponibile: se l'endpoint JSON è bloccato
            da Cloudflare/WAF.
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
            dati = sessione.get_json_xhr(_URL_RICERCA, params=parametri)
        except Exception as err:
            raise RicercaNonDisponibile(
                "La ricerca JSON non è disponibile — probabilmente Cloudflare ha bloccato "
                "la richiesta. Alternativa: usa lista_btp() per ottenere la lista dei BTP "
                f"oppure ottieni_scheda() con un ISIN noto. Errore originale: {err}"
            ) from err

        quotes = dati.get("quotes", [])
        risultati: list[RisultatoRicerca] = []

        for q in quotes:
            isin = q.get("symbol", "")
            if not isin:
                continue
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
