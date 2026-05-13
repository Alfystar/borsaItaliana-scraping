"""Scraping della pagina scheda di uno strumento su Borsa Italiana."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup, Tag

from .eccezioni import DatiNonDisponibili, StrumentoNonTrovato
from .sessione import Sessione
from .tipi import SchedaStrumento

# URL universale (segue redirect)
_URL_SCHEDA = (
    "https://www.borsaitaliana.it/borsa/search/scheda.html"
)

# URL dati completi
_URL_DATI_COMPLETI_BOND = (
    "https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/"
    "dati-completi.html"
)
_URL_DATI_COMPLETI_AZIONE = (
    "https://www.borsaitaliana.it/borsa/azioni/dati-completi.html"
)


# ------------------------------------------------------------------
# Utilità parsing numeri
# ------------------------------------------------------------------

def _pulisci_testo(testo: str) -> str:
    """Rimuove spazi extra, newline e caratteri non stampabili."""
    return " ".join(testo.split()).strip()


def _parsa_numero(testo: str, lingua: str = "en") -> Decimal | None:
    """Converte una stringa numerica in Decimal, gestendo formati EN/IT.

    - EN: ``1,234.56`` → virgola=migliaia, punto=decimale
    - IT: ``1.234,56`` → punto=migliaia, virgola=decimale
    """
    if not testo:
        return None
    testo = _pulisci_testo(testo)
    # Rimuovi simboli di valuta e percentuali
    testo = testo.replace("€", "").replace("%", "").replace("$", "").strip()
    # Gestisci il segno meno tipografico
    testo = testo.replace("−", "-").replace("–", "-")

    if not testo or testo == "-" or testo.lower() in ("n.a.", "n/a", "n.d.", "--"):
        return None

    try:
        if lingua == "it":
            # Formato IT: 1.234,56 → rimuovi punti migliaia, virgola → punto decimale
            testo = testo.replace(".", "").replace(",", ".")
        else:
            # Formato EN: 1,234.56 → rimuovi virgole migliaia
            testo = testo.replace(",", "")
        return Decimal(testo)
    except (InvalidOperation, ValueError):
        return None


def _parsa_data_scheda(testo: str) -> date | None:
    """Parsa una data dalla pagina scheda (formati vari)."""
    testo = _pulisci_testo(testo)
    if not testo or testo == "-":
        return None
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(testo, fmt).date()
        except ValueError:
            continue
    return None


def _parsa_percentuale(testo: str, lingua: str = "en") -> Decimal | None:
    """Parsa un valore percentuale, rimuovendo il simbolo %."""
    if not testo:
        return None
    testo = testo.replace("%", "").strip()
    return _parsa_numero(testo, lingua)


# ------------------------------------------------------------------
# Estrazione valori dalla pagina
# ------------------------------------------------------------------

def _trova_valore(soup: BeautifulSoup, etichette: list[str]) -> str | None:
    """Cerca coppie chiave-valore nella pagina.

    Le pagine di Borsa Italiana usano layout con label in <span>/<strong>
    seguite dal valore nella cella/div successiva.
    """
    testo_pagina = soup.get_text(" ", strip=True).lower()

    for etichetta in etichette:
        etichetta_lower = etichetta.lower()
        if etichetta_lower not in testo_pagina:
            continue

        # Strategia 1: cerco <span>/<strong> con il testo dell'etichetta
        for tag in soup.find_all(["span", "strong", "td", "th"]):
            tag_text = _pulisci_testo(tag.get_text())
            if tag_text.lower() == etichetta_lower or etichetta_lower in tag_text.lower():
                # Il valore è nel sibling successivo o nel parent → sibling
                sibling = tag.find_next_sibling()
                if sibling:
                    val = _pulisci_testo(sibling.get_text())
                    if val and val != "-":
                        return val

                # Oppure: il valore è nel tag <td> successivo (layout tabellare)
                if tag.name in ("td", "th"):
                    next_td = tag.find_next_sibling("td")
                    if next_td:
                        val = _pulisci_testo(next_td.get_text())
                        if val and val != "-":
                            return val

                # Oppure: il tag è dentro un <td>, e il valore è nel <td> successivo
                parent_td = tag.find_parent("td")
                if parent_td:
                    next_td = parent_td.find_next_sibling("td")
                    if next_td:
                        val = _pulisci_testo(next_td.get_text())
                        if val and val != "-":
                            return val

                parent_tr = tag.find_parent("tr")
                if parent_tr:
                    tds = parent_tr.find_all("td")
                    for i, td in enumerate(tds):
                        if etichetta_lower in _pulisci_testo(td.get_text()).lower():
                            if i + 1 < len(tds):
                                val = _pulisci_testo(tds[i + 1].get_text())
                                if val and val != "-":
                                    return val

    return None


def _trova_prezzo_principale(soup: BeautifulSoup, lingua: str) -> Decimal | None:
    """Estrae il prezzo principale dalla pagina (grande, in evidenza)."""
    # Cerca il container summary-value (contiene prezzo + variazione %)
    for classe in ("summary-value", "t-text -black-c", "last-price"):
        tag = soup.find(class_=re.compile(classe, re.I))
        if tag:
            # Se il tag ha figli <span>, il prezzo è nel primo (il secondo è la variazione %)
            figli_span = tag.find_all("span")
            if figli_span:
                val = _parsa_numero(_pulisci_testo(figli_span[0].get_text()), lingua)
                if val:
                    return val
            # Altrimenti prova il testo diretto
            val = _parsa_numero(_pulisci_testo(tag.get_text()), lingua)
            if val:
                return val

    # Cerca label "Last Price" / "Ultimo Prezzo" / "Price" / "Prezzo"
    etichette = ["Last Price", "Ultimo Prezzo", "Price", "Prezzo", "Last",
                 "Prezzo Ufficiale", "Official Price"]
    val_str = _trova_valore(soup, etichette)
    if val_str:
        val = _parsa_numero(val_str, lingua)
        if val:
            return val

    return None


def _determina_tipo(soup: BeautifulSoup, url_finale: str) -> str:
    """Determina il tipo di strumento dalla pagina."""
    url_lower = url_finale.lower()
    if "/obbligazioni/" in url_lower or "/mot/" in url_lower:
        return "obbligazione"
    if "/etf/" in url_lower or "/etfplus/" in url_lower:
        return "etf"
    if "/azioni/" in url_lower:
        return "azione"
    # Controlla anche il contenuto testuale
    testo = soup.get_text(" ", strip=True).lower()
    if "obbligazione" in testo or "bond" in testo or "coupon" in testo:
        return "obbligazione"
    if "etf" in testo:
        return "etf"
    return "azione"


def _estrai_nome(soup: BeautifulSoup) -> str:
    """Estrae il nome dello strumento dalla pagina."""
    # Cerca il tag <h1>
    h1 = soup.find("h1")
    if h1:
        nome = _pulisci_testo(h1.get_text())
        if nome:
            return nome
    # Fallback: titolo della pagina
    title = soup.find("title")
    if title:
        return _pulisci_testo(title.get_text()).split("|")[0].strip()
    return "Sconosciuto"


def _estrai_mercato(soup: BeautifulSoup, lingua: str) -> str:
    """Estrae il mercato di negoziazione."""
    etichette = ["Market", "Mercato", "Mercato di quotazione",
                 "Quotation Market", "Market Segment"]
    val = _trova_valore(soup, etichette)
    return val if val else "MOT"


def _estrai_valuta(soup: BeautifulSoup, lingua: str) -> str:
    """Estrae la valuta di negoziazione, default EUR."""
    etichette = [
        "Negotiation Currency", "Negotiation currency",
        "Valuta di Negoziazione", "Valuta di negoziazione",
        "Trading Currency", "Settlement Currency",
        "Valuta di Liquidazione", "Valuta",
    ]
    val = _trova_valore(soup, etichette)
    if val:
        val = val.strip().upper()
        if len(val) == 3 and val.isalpha():
            return val
    return "EUR"


# ------------------------------------------------------------------
# Funzione principale
# ------------------------------------------------------------------

def ottieni_scheda(
    isin: str,
    mic: str | None = None,
    lingua: str = "en",
    sessione: Sessione | None = None,
) -> SchedaStrumento:
    """Esegue lo scraping della pagina scheda di uno strumento.

    Args:
        isin: codice ISIN dello strumento.
        mic: codice MIC (es. ``"MOTX"``). Se ``None`` usa l'URL
            universale con redirect automatico.
        lingua: ``"en"`` (consigliata) o ``"it"``.
        sessione: sessione HTTP riutilizzabile.

    Returns:
        ``SchedaStrumento`` con tutti i dati estratti.

    Raises:
        StrumentoNonTrovato: se la pagina non esiste.
        DatiNonDisponibili: se il prezzo non è leggibile.
    """
    isin = isin.strip().upper()
    lingua = lingua.lower()

    sessione_locale = sessione is None
    if sessione_locale:
        sessione = Sessione()

    try:
        # Scarica la pagina scheda
        parametri: dict[str, str] = {"code": isin, "lang": lingua}
        if mic:
            parametri["mic"] = mic

        soup = sessione.get_html(_URL_SCHEDA, params=parametri)

        # Controlla se la pagina esiste
        testo_pagina = soup.get_text(" ", strip=True)
        if any(msg in testo_pagina for msg in ("Page not found", "Pagina non trovata", "404")):
            raise StrumentoNonTrovato(f"Pagina scheda non trovata per ISIN '{isin}'")

        # Determina tipo e URL finale (dopo eventuali redirect)
        url_finale = ""
        base_tag = soup.find("link", rel="canonical")
        if base_tag and isinstance(base_tag, Tag) and base_tag.get("href"):
            url_finale = str(base_tag["href"])

        tipo = _determina_tipo(soup, url_finale)
        nome = _estrai_nome(soup)
        mercato = _estrai_mercato(soup, lingua)
        valuta = _estrai_valuta(soup, lingua)

        # Prezzo principale
        prezzo = _trova_prezzo_principale(soup, lingua)
        if prezzo is None:
            # Tentativo: provo la pagina dati-completi
            try:
                soup_dc = _scarica_dati_completi(isin, tipo, lingua, sessione, mic)
                prezzo = _trova_prezzo_principale(soup_dc, lingua)
                # Estrai dati aggiuntivi dalla pagina dati-completi
                soup = soup_dc
            except Exception:
                pass

        if prezzo is None:
            raise DatiNonDisponibili(
                f"Impossibile estrarre il prezzo dalla pagina scheda di '{isin}'"
            )

        # Variazione %
        variazione_str = _trova_valore(soup, [
            "Var %", "Var%", "Change %", "Variazione %", "Var. %", "Perf.",
        ])
        variazione = _parsa_percentuale(variazione_str, lingua) if variazione_str else None

        # Costruisci il risultato base
        scheda = SchedaStrumento(
            isin=isin,
            nome=nome,
            prezzo=prezzo,
            variazione_percentuale=variazione,
            valuta=valuta,
            tipo=tipo,
            mercato=mercato,
        )

        # Campi specifici per obbligazioni
        if tipo == "obbligazione":
            _arricchisci_obbligazione(scheda, soup, lingua)

        # Campi specifici per azioni
        if tipo == "azione":
            _arricchisci_azione(scheda, soup, lingua)

        return scheda

    finally:
        if sessione_locale:
            sessione.chiudi()


def _scarica_dati_completi(
    isin: str,
    tipo: str,
    lingua: str,
    sessione: Sessione,
    mic: str | None = None,
) -> BeautifulSoup:
    """Scarica la pagina dati-completi per uno strumento."""
    if tipo == "obbligazione":
        url = _URL_DATI_COMPLETI_BOND
    else:
        url = _URL_DATI_COMPLETI_AZIONE

    parametri: dict[str, str] = {"isin": isin, "lang": lingua}
    if mic:
        parametri["mic"] = mic

    return sessione.get_html(url, params=parametri)


def _arricchisci_obbligazione(
    scheda: SchedaStrumento,
    soup: BeautifulSoup,
    lingua: str,
) -> None:
    """Popola i campi specifici per obbligazioni."""
    # Rendimento lordo
    val = _trova_valore(soup, [
        "Gross Yield", "Rendimento Lordo", "YTM Gross",
        "Gross Yield to Maturity",
    ])
    scheda.rendimento_lordo = _parsa_percentuale(val, lingua) if val else None

    # Rendimento netto
    val = _trova_valore(soup, [
        "Net Yield", "Rendimento Netto", "YTM Net",
        "Net Yield to Maturity",
    ])
    scheda.rendimento_netto = _parsa_percentuale(val, lingua) if val else None

    # Rateo lordo
    val = _trova_valore(soup, [
        "Gross Accrued Interest", "Rateo Lordo",
        "Accrued Interest Gross",
    ])
    scheda.rateo_lordo = _parsa_numero(val, lingua) if val else None

    # Rateo netto
    val = _trova_valore(soup, [
        "Net Accrued Interest", "Rateo Netto",
        "Accrued Interest Net",
    ])
    scheda.rateo_netto = _parsa_numero(val, lingua) if val else None

    # Duration modificata
    val = _trova_valore(soup, [
        "Modified Duration", "Duration Modificata",
        "Mod. Duration",
    ])
    scheda.duration_modificata = _parsa_numero(val, lingua) if val else None

    # Cedola annua
    val = _trova_valore(soup, [
        "Annual Coupon Rate", "Cedola Annua",
        "Annual Coupon", "Tasso Cedola Annuale",
    ])
    scheda.cedola_annua = _parsa_percentuale(val, lingua) if val else None

    # Cedola periodale
    val = _trova_valore(soup, [
        "Periodic Coupon Rate", "Cedola Periodale",
        "Periodic Coupon", "Tasso Cedola Periodale",
    ])
    scheda.cedola_periodale = _parsa_percentuale(val, lingua) if val else None

    # Scadenza
    val = _trova_valore(soup, [
        "Maturity Date", "Scadenza", "Maturity",
        "Data Scadenza",
    ])
    scheda.scadenza = _parsa_data_scheda(val) if val else None

    # Emittente
    val = _trova_valore(soup, [
        "Issuer", "Emittente", "Issuer Name",
    ])
    scheda.emittente = val

    # Tipo bond
    val = _trova_valore(soup, [
        "Coupon Type", "Tipo Cedola", "Bond Type",
        "Tipo Obbligazione",
    ])
    scheda.tipo_bond = val

    # Lotto minimo
    val = _trova_valore(soup, [
        "Minimum Lot", "Lotto Minimo", "Min. Lot",
        "Min Lot",
    ])
    if val:
        numero = _parsa_numero(val, lingua)
        scheda.lotto_minimo = int(numero) if numero else None

    # Descrizione payout
    val = _trova_valore(soup, [
        "Payout Description", "Descrizione Payout",
        "Coupon Description",
    ])
    scheda.descrizione_payout = val


def _arricchisci_azione(
    scheda: SchedaStrumento,
    soup: BeautifulSoup,
    lingua: str,
) -> None:
    """Popola i campi specifici per azioni."""
    # Settore
    val = _trova_valore(soup, [
        "Super Sector", "Settore", "Sector",
        "Industry Sector",
    ])
    scheda.settore = val

    # Capitalizzazione
    val = _trova_valore(soup, [
        "Market Cap", "Capitalizzazione", "Market Capitalization",
        "Cap. di Mercato",
    ])
    scheda.capitalizzazione = _parsa_numero(val, lingua) if val else None

    # Ticker
    val = _trova_valore(soup, [
        "Alphanumeric Code", "Codice Alfanumerico", "Ticker",
        "Symbol", "Alpha Code",
    ])
    scheda.ticker = val

    # Performance 1 mese
    val = _trova_valore(soup, [
        "Perf. 1 month", "Perf. 1 mese", "Performance 1M",
        "Perf 1M", "1 Month",
    ])
    scheda.performance_1m = _parsa_percentuale(val, lingua) if val else None

    # Performance 6 mesi
    val = _trova_valore(soup, [
        "Perf. 6 months", "Perf. 6 mesi", "Performance 6M",
        "Perf 6M", "6 Months",
    ])
    scheda.performance_6m = _parsa_percentuale(val, lingua) if val else None

    # Performance 1 anno
    val = _trova_valore(soup, [
        "Perf. 1 year", "Perf. 1 anno", "Performance 1Y",
        "Perf 1Y", "1 Year",
    ])
    scheda.performance_1y = _parsa_percentuale(val, lingua) if val else None
