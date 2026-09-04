"""Test di integrazione per i mercati non-XMIL (EuroTLX, ExtraMOT).

Canary: se Borsa Italiana cambia la risoluzione mic/platform o la grafici API,
questi test devono rompersi per primi.
"""

from datetime import date
from decimal import Decimal

import pytest

from borsa_italiana_scraping import (
    DatiNonDisponibili,
    PrezzoCorrente,
    Sessione,
    StrumentoNonRisolto,
    StrumentoNonTrovato,
    ottieni_prezzo_corrente,
    ottieni_scheda,
    ottieni_storico,
)

ISIN_TBOND_ETLX = "US912810TU25"  # T-Bond USA 4.375% Aug43, quotato su EuroTLX, in USD
ISIN_AIRBUS_XMOT = "XS1128224703"  # Airbus 2.125% Ot29, ExtraMOT (illiquido)


@pytest.fixture(scope="module")
def sessione():
    s = Sessione()
    yield s
    s.chiudi()


@pytest.mark.integration
class TestSchedaEuroTLX:
    """La pagina universale non redirige per EuroTLX senza mic+platform."""

    def test_senza_mic_solleva_non_risolto(self, sessione: Sessione) -> None:
        with pytest.raises(StrumentoNonRisolto):
            ottieni_scheda(ISIN_TBOND_ETLX, lingua="it", sessione=sessione)

    def test_con_mic_e_platform(self, sessione: Sessione) -> None:
        scheda = ottieni_scheda(ISIN_TBOND_ETLX, mic="ETLX", platform="TLX", lingua="it", sessione=sessione)

        assert scheda.tipo == "obbligazione"
        assert isinstance(scheda.prezzo, Decimal) and scheda.prezzo > 0
        assert scheda.valuta == "USD"  # bond denominato in dollari
        assert scheda.url_pagina and "/obbligazioni/eurotlx/scheda/" in scheda.url_pagina

    def test_emittente_da_dati_completi(self, sessione: Sessione) -> None:
        """Emittente/scadenza arrivano da dati-completi (derivato dall'URL finale)."""
        scheda = ottieni_scheda(ISIN_TBOND_ETLX, mic="ETLX", platform="TLX", lingua="it", sessione=sessione)

        assert scheda.emittente is not None
        assert "united states" in scheda.emittente.lower()
        assert isinstance(scheda.scadenza, date)


@pytest.mark.integration
class TestStoricoEuroTLX:
    """La grafici API conosce EuroTLX solo sotto l'exchCode ETLX."""

    def test_exchange_esplicito(self, sessione: Sessione) -> None:
        r = ottieni_storico(ISIN_TBOND_ETLX, periodo="1M", sessione=sessione, exchange="ETLX")

        assert len(r.punti) > 0
        assert r.codice_borsa == "ETLX"
        assert r.valuta == "USD"

    def test_auto_discovery(self, sessione: Sessione) -> None:
        """Senza exchange: XMIL fallisce, la site-search scopre ETLX."""
        r = ottieni_storico(ISIN_TBOND_ETLX, periodo="1M", sessione=sessione)

        assert len(r.punti) > 0
        assert r.valuta == "USD"

    def test_extramot_finestra_vuota_non_e_sconosciuto(self, sessione: Sessione) -> None:
        """ExtraMOT illiquido: finestra 1M vuota ⇒ DatiNonDisponibili, MAI StrumentoNonTrovato."""
        try:
            r = ottieni_storico(ISIN_AIRBUS_XMOT, periodo="1M", sessione=sessione)
            assert r.punti is not None  # ha ripreso a scambiare: comunque riconosciuto
        except DatiNonDisponibili:
            pass  # atteso: noto ma senza scambi nella finestra
        except StrumentoNonTrovato:
            pytest.fail("XMOT 1M deve essere 'finestra vuota', non 'strumento non trovato'")


@pytest.mark.integration
class TestPrezzoEuroTLX:
    def test_prezzo_corrente(self, sessione: Sessione) -> None:
        prezzo = ottieni_prezzo_corrente(ISIN_TBOND_ETLX, sessione=sessione)

        assert isinstance(prezzo, PrezzoCorrente)
        assert prezzo.prezzo > 0
        assert prezzo.valuta == "USD"
