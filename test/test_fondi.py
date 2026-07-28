"""Test unitari (offline) per l'estrazione dei dettagli dalla pagina-fondo.

Verificano il parsing delle sezioni descrittive (Caratteristiche / Società di
Gestione / Costi) senza richieste reali al sito, usando una fixture HTML che
riproduce la struttura ``<h3>`` + ``<table>`` delle pagine-fondo di Borsa
Italiana, incluso il caso di una sezione **senza** tabella propria (valori tutti
"N.D.") e i placeholder "N.D." da scartare.
"""

from bs4 import BeautifulSoup

from borsa_italiana_scraping.fondi import (
    _e_non_disponibile,
    _estrai_dettagli_sezione,
    _norm_heading,
)

# Riproduce l'ordine reale del DOM: la sezione "Società di Gestione" non ha una
# tabella propria (subito dopo arriva l'heading "Costi").
_HTML_FONDO = """
<h1>Eurizon Next 2.0 Alloc. Divers. 40 P Cap Eur</h1>
<h3>Andamento</h3>
<table><tr><td>Ultima</td><td>Precedente</td></tr></table>
<h3>Caratteristiche</h3>
<table>
  <tr><td>Isin</td><td>LU2178929613</td></tr>
  <tr><td>Tipologia</td><td>N.D.</td></tr>
  <tr><td>Valuta</td><td>EUR</td></tr>
  <tr><td>Classe</td><td>P</td></tr>
  <tr><td>Grado di Rischio</td><td>3</td></tr>
  <tr><td>Categoria Assogestioni</td><td>Bilanciati</td></tr>
  <tr><td>Nome del gestore</td><td>N.D.</td></tr>
</table>
<h3>Società di Gestione</h3>
<h3>Costi</h3>
<table>
  <tr><td>Ingresso (PAC)</td><td>Min: 0,0000 - Max: 0,0000</td></tr>
  <tr><td>Gestione</td><td>1.3</td></tr>
  <tr><td>Rimborso</td><td>0%</td></tr>
  <tr><td>Amministrative</td><td>N.D.</td></tr>
</table>
"""


def _soup() -> BeautifulSoup:
    return BeautifulSoup(_HTML_FONDO, "html.parser")


class TestEstraiDettagliSezione:
    def test_caratteristiche_scarta_nd_ed_esclusi(self) -> None:
        dettagli = _estrai_dettagli_sezione(_soup(), "Caratteristiche", escludi=("Isin", "Valuta"))
        assert dettagli == {
            "Classe": "P",
            "Grado di Rischio": "3",
            "Categoria Assogestioni": "Bilanciati",
        }

    def test_costi_scarta_nd(self) -> None:
        dettagli = _estrai_dettagli_sezione(_soup(), "Costi")
        assert dettagli == {
            "Ingresso (PAC)": "Min: 0,0000 - Max: 0,0000",
            "Gestione": "1.3",
            "Rimborso": "0%",
        }

    def test_sezione_senza_tabella_ritorna_vuoto(self) -> None:
        # "Società di Gestione" è seguita subito dall'heading "Costi": nessuna
        # tabella propria → non deve sforare sulla tabella dei Costi.
        assert _estrai_dettagli_sezione(_soup(), "Società di Gestione") == {}

    def test_heading_insensibile_ad_accenti_e_maiuscole(self) -> None:
        assert _estrai_dettagli_sezione(_soup(), "SOCIETA DI GESTIONE") == {}

    def test_heading_inesistente_ritorna_vuoto(self) -> None:
        assert _estrai_dettagli_sezione(_soup(), "Inesistente") == {}


class TestHelper:
    def test_e_non_disponibile(self) -> None:
        for v in ["N.D.", "N.d.", "ND", "n.d.", "-", "--", "", "  N.D.  "]:
            assert _e_non_disponibile(v) is True, v
        for v in ["1.3", "0%", "Bilanciati", "3"]:
            assert _e_non_disponibile(v) is False, v

    def test_norm_heading(self) -> None:
        assert _norm_heading("Società  di  Gestione") == "societa di gestione"
        assert _norm_heading("Caratteristiche") == "caratteristiche"
