"""Eccezioni personalizzate per borsa-italiana-scraping."""


class BorsaItalianaErrore(Exception):
    """Errore base della libreria."""
    pass


class StrumentoNonTrovato(BorsaItalianaErrore):
    """Lo strumento con l'ISIN specificato non è stato trovato."""
    pass


class DatiNonDisponibili(BorsaItalianaErrore):
    """I dati richiesti non sono disponibili (periodo non supportato, mercato chiuso, ecc.)."""
    pass


class ErroreConnessione(BorsaItalianaErrore):
    """Errore di rete o timeout."""
    pass


class RateLimitRaggiunto(BorsaItalianaErrore):
    """Troppe richieste — il WAF ha bloccato la connessione."""
    pass


class RicercaNonDisponibile(BorsaItalianaErrore):
    """La ricerca JSON non è disponibile (Cloudflare block). Suggerisce di usare lista_btp() ecc."""
    pass
