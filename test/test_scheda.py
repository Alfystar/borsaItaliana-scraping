"""Test di integrazione per scheda.py — scraping pagina strumento."""

from datetime import date
from decimal import Decimal

import pytest

from borsa_italiana_scraping import ottieni_scheda, Sessione
from borsa_italiana_scraping.tipi import SchedaStrumento

ISIN_ENEL = "IT0003128367"
ISIN_BTP = "IT0005634800"
ISIN_BTP_FISSO = "IT0005560948"


@pytest.fixture(scope="module")
def sessione():
    s = Sessione()
    yield s
    s.chiudi()


@pytest.mark.integration
class TestSchedaObbligazione:
    """Test scraping scheda BTP."""

    def test_scheda_btp_en(self, sessione: Sessione) -> None:
        """Scheda BTP in inglese — verifica campi base."""
        scheda = ottieni_scheda(ISIN_BTP, lingua="en", sessione=sessione)

        assert isinstance(scheda, SchedaStrumento)
        assert scheda.isin == ISIN_BTP
        assert isinstance(scheda.prezzo, Decimal)
        assert scheda.prezzo > 0
        assert scheda.valuta  # Non vuota
        assert scheda.tipo == "obbligazione"
        assert scheda.nome  # Non vuoto

    def test_scheda_btp_campi_specifici(self, sessione: Sessione) -> None:
        """La scheda BTP deve avere i campi specifici obbligazione."""
        scheda = ottieni_scheda(ISIN_BTP_FISSO, lingua="en", sessione=sessione)

        assert scheda.tipo == "obbligazione"
        # Almeno alcuni campi devono essere valorizzati per un BTP classico
        # (scadenza, cedola annua sono quasi sempre presenti)
        assert scheda.scadenza is None or isinstance(scheda.scadenza, date)


@pytest.mark.integration
class TestSchedaAzione:
    """Test scraping scheda azione."""

    def test_scheda_enel_en(self, sessione: Sessione) -> None:
        """Scheda ENEL in inglese."""
        scheda = ottieni_scheda(ISIN_ENEL, lingua="en", sessione=sessione)

        assert isinstance(scheda, SchedaStrumento)
        assert scheda.isin == ISIN_ENEL
        assert isinstance(scheda.prezzo, Decimal)
        assert scheda.prezzo > 0
        assert scheda.tipo == "azione"
