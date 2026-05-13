#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════
  WALKTEST — Tour interattivo della libreria borsa-italiana-scraping
═══════════════════════════════════════════════════════════════════

Esegui con:
    pipenv run python esempi/walktest.py

Ogni step si ferma con [Invio] per darti tempo di leggere.
Puoi anche eseguire ogni sezione singolarmente dall'IDE selezionando
il blocco e facendo "Run Selection".
"""

from borsa_italiana_scraping import (
    Sessione,
    ottieni_storico,
    ottieni_intraday,
    ottieni_prezzo_corrente,
    ottieni_scheda,
    lista_btp,
    cerca,
    DatiNonDisponibili,
)

ISIN_ENEL = "IT0003128367"
ISIN_BTP_PIU = "IT0005634800"
ISIN_BTP_FISSO = "IT0005560948"


def pausa(msg: str = "") -> None:
    input(f"\n{'─' * 60}\n  ▶ {msg or 'Premi Invio per continuare...'}\n")


def step_1_sessione(sess: Sessione) -> None:
    """STEP 1 — Sessione e warmup JWT"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║  STEP 1: Sessione HTTP + Warmup JWT                        ║
╚══════════════════════════════════════════════════════════════╝

La classe Sessione gestisce:
  • Estrazione automatica del JWT token dall'interactive-chart
  • Cookie Imperva WAF
  • Rate limiting (pausa tra richieste)
  • Retry con backoff esponenziale
""")
    print(f"  Token JWT:   {'✅ presente' if sess._token else '❌ mancante'}")
    print(f"  Warmup:      {'✅ eseguito' if sess._warmup_eseguito else '❌ non eseguito'}")
    print(f"  Cookie:      {len(sess._client.cookies.jar)} cookie attivi")


def step_2_storico(sess: Sessione) -> None:
    """STEP 2 — Dati storici OHLCV (JSON API)"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║  STEP 2: Dati storici OHLCV                                ║
╚══════════════════════════════════════════════════════════════╝

Fonte:  JSON API grafici.borsaitaliana.it
Periodi: 1M, 3M, 6M, 1Y, 3Y, 5Y, MAX
""")

    # ENEL — azione
    storico = ottieni_storico(ISIN_ENEL, periodo="1Y", sessione=sess)
    print(f"  📈 ENEL ({ISIN_ENEL}) — Storico 1Y")
    print(f"     Borsa: {storico.codice_borsa}")
    print(f"     Punti: {len(storico.punti)}")
    print(f"     Range date: {storico.punti[0].data} → {storico.punti[-1].data}")
    print()
    print("     Ultimi 5 giorni:")
    for p in storico.punti[-5:]:
        print(f"       {p.data}  O={p.apertura:>8}  H={p.massimo:>8}  "
              f"L={p.minimo:>8}  C={p.chiusura:>8}  V={p.volume:>12,}")

    print()

    # BTP — obbligazione
    storico_btp = ottieni_storico(ISIN_BTP_PIU, periodo="3M", sessione=sess)
    print(f"  📈 BTP Più ({ISIN_BTP_PIU}) — Storico 3M")
    print(f"     Punti: {len(storico_btp.punti)}")
    if storico_btp.punti:
        p = storico_btp.punti[-1]
        print(f"     Ultimo: {p.data} C={p.chiusura}")


def step_3_intraday(sess: Sessione) -> None:
    """STEP 3 — Dati intraday (JSON API)"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║  STEP 3: Dati intraday                                     ║
╚══════════════════════════════════════════════════════════════╝

Fonte:  JSON API grafici.borsaitaliana.it
Risoluzioni: 1MN, 5MN, 15MN, 30MN, 1H
⚠ Disponibile solo durante l'orario di borsa (09:00–17:35)
""")

    try:
        intraday = ottieni_intraday(ISIN_ENEL, risoluzione="5MN", sessione=sess)
        print(f"  ⏱️ ENEL intraday 5MN: {len(intraday.punti)} candele")
        if intraday.punti:
            print("     Ultime 3:")
            for p in intraday.punti[-3:]:
                print(f"       {p.orario.strftime('%H:%M')}  "
                      f"O={p.apertura:>8}  C={p.chiusura:>8}  V={p.volume:>10,}")
    except DatiNonDisponibili:
        print("  ⚠ Mercato chiuso — nessun dato intraday disponibile")


def step_4_prezzo_corrente(sess: Sessione) -> None:
    """STEP 4 — Prezzo corrente (API + fallback scraping)"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║  STEP 4: Prezzo corrente                                   ║
╚══════════════════════════════════════════════════════════════╝

Strategia a 2 livelli:
  1° tentativo: JSON API (ultimo punto storico 1M)
  2° fallback:  Scraping della pagina scheda HTML
""")

    for isin, nome in [(ISIN_ENEL, "ENEL"), (ISIN_BTP_PIU, "BTP Più")]:
        prezzo = ottieni_prezzo_corrente(isin, sessione=sess)
        print(f"  💰 {nome}: {prezzo.prezzo} {prezzo.valuta}")
        print(f"     Variazione: {prezzo.variazione_percentuale}%")
        print(f"     Data: {prezzo.data}")
        print(f"     Fonte: {prezzo.fonte}")
        print()


def step_5_scheda(sess: Sessione) -> None:
    """STEP 5 — Scheda strumento (scraping HTML)"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║  STEP 5: Scheda strumento (metadati ricchi)                ║
╚══════════════════════════════════════════════════════════════╝

Fonte: Scraping HTML della pagina scheda su www.borsaitaliana.it
Campi: variano in base al tipo (azione vs obbligazione)
""")

    # Obbligazione
    scheda = ottieni_scheda(ISIN_BTP_PIU, lingua="en", sessione=sess)
    print(f"  📋 {scheda.nome} ({scheda.isin})")
    print(f"     Tipo:              {scheda.tipo}")
    print(f"     Prezzo:            {scheda.prezzo} {scheda.valuta}")
    print(f"     Variazione:        {scheda.variazione_percentuale}%")
    print(f"     Mercato:           {scheda.mercato}")
    print(f"     --- Campi obbligazione ---")
    print(f"     Rendimento lordo:  {scheda.rendimento_lordo}")
    print(f"     Rendimento netto:  {scheda.rendimento_netto}")
    print(f"     Cedola annua:      {scheda.cedola_annua}")
    print(f"     Duration mod.:     {scheda.duration_modificata}")
    print(f"     Rateo lordo:       {scheda.rateo_lordo}")
    print(f"     Scadenza:          {scheda.scadenza}")
    print()

    # Azione
    scheda_az = ottieni_scheda(ISIN_ENEL, lingua="en", sessione=sess)
    print(f"  📋 {scheda_az.nome} ({scheda_az.isin})")
    print(f"     Tipo:              {scheda_az.tipo}")
    print(f"     Prezzo:            {scheda_az.prezzo} {scheda_az.valuta}")
    print(f"     Mercato:           {scheda_az.mercato}")
    print(f"     --- Campi azione ---")
    print(f"     Settore:           {scheda_az.settore}")
    print(f"     Capitalizzazione:  {scheda_az.capitalizzazione}")
    print(f"     Ticker:            {scheda_az.ticker}")
    print(f"     Perf 1M:           {scheda_az.performance_1m}")
    print(f"     Perf 6M:           {scheda_az.performance_6m}")
    print(f"     Perf 1Y:           {scheda_az.performance_1y}")


def step_6_lista(sess: Sessione) -> None:
    """STEP 6 — Lista BTP (scraping tabella HTML)"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║  STEP 6: Lista BTP quotati sul MOT                         ║
╚══════════════════════════════════════════════════════════════╝

Fonte: Scraping della tabella HTML su www.borsaitaliana.it
""")

    btp = lista_btp(lingua="en", sessione=sess)
    print(f"  📃 Trovati {len(btp)} BTP")
    print()
    print(f"  {'ISIN':<14} {'Nome':<30} {'Prezzo':>10} {'Cedola':>8} {'Scadenza':>12}")
    print(f"  {'─' * 14} {'─' * 30} {'─' * 10} {'─' * 8} {'─' * 12}")
    for b in btp[:10]:
        prezzo = str(b.ultimo_prezzo or "—")
        cedola = str(b.cedola or "—")
        scad = str(b.scadenza or "—")
        print(f"  {b.isin:<14} {b.nome[:30]:<30} {prezzo:>10} {cedola:>8} {scad:>12}")
    if len(btp) > 10:
        print(f"  ... e altri {len(btp) - 10}")


def step_7_ricerca(sess: Sessione) -> None:
    """STEP 7 — Ricerca strumenti (JSON endpoint interno)"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║  STEP 7: Ricerca strumenti                                 ║
╚══════════════════════════════════════════════════════════════╝

Fonte: Endpoint JSON /borsa/searchengine/all/json/search.html
Non richiede JWT né header XHR — endpoint pubblico.
""")

    for query in ("ENEL", "BTP", "IT0005634800"):
        print(f"  🔍 Ricerca: '{query}'")
        risultati = cerca(query, lingua="it", sessione=sess)
        print(f"     Trovati: {len(risultati)}")
        for r in risultati[:3]:
            print(f"       {r.isin} | {r.nome[:35]} | {r.tipo} | {r.mercato}")
        print()


def main() -> None:
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                            ║
║   📈 borsa-italiana-scraping — WALKTEST INTERATTIVO        ║
║                                                            ║
║   Tour guidato di tutte le funzionalità della libreria.    ║
║   Ogni step effettua richieste reali a borsaitaliana.it    ║
║                                                            ║
╚══════════════════════════════════════════════════════════════╝
""")

    pausa("Iniziamo! Verrà creata la sessione HTTP con warmup JWT...")

    with Sessione() as sess:
        step_1_sessione(sess)
        pausa("Prossimo: dati storici OHLCV (JSON API)...")

        step_2_storico(sess)
        pausa("Prossimo: dati intraday...")

        step_3_intraday(sess)
        pausa("Prossimo: prezzo corrente (API + fallback scraping)...")

        step_4_prezzo_corrente(sess)
        pausa("Prossimo: scheda strumento (scraping HTML)...")

        step_5_scheda(sess)
        pausa("Prossimo: lista BTP...")

        step_6_lista(sess)
        pausa("Prossimo: ricerca strumenti (ultima feature)...")

        step_7_ricerca(sess)

    print("""
╔══════════════════════════════════════════════════════════════╗
║  ✅ WALKTEST COMPLETATO                                    ║
║                                                            ║
║  Riepilogo funzionalità testate:                           ║
║    1. Sessione HTTP + JWT warmup automatico                ║
║    2. Dati storici OHLCV (JSON API, 7 periodi)             ║
║    3. Dati intraday (JSON API, 5 risoluzioni)              ║
║    4. Prezzo corrente (API + fallback scraping)             ║
║    5. Scheda strumento (metadati: bond + equity)            ║
║    6. Lista BTP quotati (scraping tabella)                  ║
║    7. Ricerca strumenti (JSON endpoint, nessun WAF)          ║
╚══════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
