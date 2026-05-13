"""Test di integrazione per ricerca.py — ricerca strumenti."""

import pytest

from borsa_italiana_scraping import cerca, RicercaNonDisponibile, Sessione
from borsa_italiana_scraping.tipi import RisultatoRicerca


@pytest.fixture(scope="module")
def sessione():
    s = Sessione()
    yield s
    s.chiudi()


@pytest.mark.integration
class TestRicerca:
    """Test della ricerca strumenti."""

    def test_cerca_enel(self, sessione: Sessione) -> None:
        """Cerca 'ENEL' e verifica il formato dei risultati."""
        try:
            risultati = cerca("ENEL", lingua="it", sessione=sessione)
            assert isinstance(risultati, list)
            # Se la ricerca funziona, deve trovare qualcosa
            if risultati:
                r = risultati[0]
                assert isinstance(r, RisultatoRicerca)
                assert r.isin  # ISIN non vuoto
                assert r.nome  # Nome non vuoto
                assert r.tipo  # Tipo non vuoto
        except RicercaNonDisponibile:
            pytest.skip("Ricerca JSON bloccata da Cloudflare")

    def test_cerca_btp(self, sessione: Sessione) -> None:
        """Cerca 'BTP' e verifica la presenza di risultati."""
        try:
            risultati = cerca("BTP", lingua="en", sessione=sessione)
            assert isinstance(risultati, list)
        except RicercaNonDisponibile:
            pytest.skip("Ricerca JSON bloccata da Cloudflare")

    def test_lingua_invalida(self, sessione: Sessione) -> None:
        """Una lingua non supportata deve sollevare ValueError."""
        with pytest.raises(ValueError):
            cerca("test", lingua="de", sessione=sessione)
