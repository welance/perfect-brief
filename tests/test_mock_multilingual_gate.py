"""The offline judge reads the gate rules in the Directory's languages, not
only English: a brief that clearly states a boundary, a title or a problem in
Italian/German/French/Spanish/Portuguese/Dutch/Polish must not be reported as
open-ended, untitled or solution-first."""

import pytest

from brief_bar import load_bundled
from brief_bar.judge import MockJudge

RULES, _ = load_bundled()


def _status(rule_id, text):
    return MockJudge().judge(RULES[rule_id], text, "brief").status.value


EXPLICIT = [
    ("it", "Fuori perimetro: il canale di vendita online."),
    ("it", "Fuori scope: i pagamenti."),
    ("it", "Fuori ambito: la migrazione dei dati."),
    ("it", "Non implementeremo un sistema di cassa."),
    ("it", "Il magazzino non rientra nel progetto."),
    ("it", "Il modulo ordini è escluso."),
    ("de", "Nicht im Umfang: die mobile App."),
    ("de", "Außerhalb des Umfangs liegt das Reporting."),
    ("de", "Die Migration ist ausgeschlossen."),
    ("de", "Das Hosting ist nicht Teil des Projekts."),
    ("fr", "Hors périmètre : la refonte du site."),
    ("fr", "Le paiement est hors du périmètre."),
    ("fr", "Le module de stock est exclu."),
    ("fr", "L'hébergement ne fait pas partie du projet."),
    ("es", "Fuera del alcance: la app móvil."),
    ("es", "El módulo de pagos está excluido."),
    ("es", "El proyecto no incluye el alojamiento."),
    ("pt", "Fora do escopo: o aplicativo móvel."),
    ("pt-BR", "Fora do escopo: a migração de dados."),
    ("pt", "Fora do âmbito: a hospedagem."),
    ("pt", "O módulo de pagamentos está excluído."),
    ("nl", "Buiten scope: de mobiele app."),
    ("nl", "Betalingen vallen buiten de scope."),
    ("nl", "Hosting is uitgesloten."),
    ("pl", "Poza zakresem: aplikacja mobilna."),
    ("pl", "Migracja danych jest wykluczone."),
]

SOFT = [
    ("it", "Per ora ci concentriamo sulle prenotazioni."),
    ("it", "Inizialmente solo la versione web."),
    ("de", "Vorerst nur die Webversion."),
    ("de", "Zunächst konzentrieren wir uns auf Buchungen."),
    ("fr", "Pour l'instant, seulement la version web."),
    ("fr", "Dans un premier temps, les réservations."),
    ("es", "Por ahora solo la versión web."),
    ("es", "Inicialmente, las reservas."),
    ("pt", "Por enquanto só a versão web."),
    ("pt-BR", "Na primeira fase, só as reservas. Inicialmente web."),
    ("nl", "Voorlopig alleen de webversie."),
    ("nl", "In eerste instantie de boekingen."),
    ("pl", "Na razie tylko wersja webowa."),
    ("pl", "Początkowo tylko rezerwacje."),
]

NONE = [
    ("it", "Vogliamo un portale per gestire le prenotazioni e i clienti."),
    ("de", "Wir brauchen ein Portal für Buchungen und Kunden."),
    ("fr", "Nous voulons un portail pour les réservations et les clients."),
    ("es", "Queremos un portal para reservas y clientes."),
    ("pt", "Queremos um portal para reservas e clientes."),
    ("nl", "Wij willen een portaal voor boekingen en klanten."),
    ("pl", "Chcemy portal do rezerwacji i klientów."),
]


@pytest.mark.parametrize("lang,text", EXPLICIT, ids=[f"{lang}-{i}" for i, (lang, _) in enumerate(EXPLICIT)])
def test_explicit_boundary_passes(lang, text):
    assert _status("scope-boundaries", text) == "pass"


@pytest.mark.parametrize("lang,text", SOFT, ids=[f"{lang}-{i}" for i, (lang, _) in enumerate(SOFT)])
def test_soft_boundary_is_partial(lang, text):
    assert _status("scope-boundaries", text) == "partial"


@pytest.mark.parametrize("lang,text", NONE, ids=[lang for lang, _ in NONE])
def test_no_boundary_fails(lang, text):
    assert _status("scope-boundaries", text) == "fail"


def test_real_world_italian_boundary_section():
    text = (
        "Fuori perimetro\n"
        "Il canale di vendita online delle camere, che resta sui portali e sul gestionale esistente. "
        "Non sostituiamo il gestionale camere: lo leggiamo.\n\n"
        "Non implementeremo un sistema di gestione dei tavoli."
    )
    assert _status("scope-boundaries", text) == "pass"


@pytest.mark.parametrize("label", ["Titolo", "Titel", "Titre", "Título", "Tytuł"])
def test_localised_title_label_passes(label):
    assert _status("clear-title", f"{label}: Portale prenotazioni\n\nTesto del brief.") == "pass"


PROBLEM = [
    ("it", "Perdiamo prenotazioni perché non abbiamo un sistema unico."),
    ("de", "Wir verlieren Buchungen, weil wir kein zentrales System haben."),
    ("fr", "Nous perdons des réservations parce que nous n'avons pas de système unique."),
    ("es", "Perdemos reservas porque no tenemos un sistema único."),
    ("pt", "Perdemos reservas porque não temos um sistema único."),
    ("nl", "We verliezen boekingen omdat we geen centraal systeem hebben."),
    ("pl", "Tracimy rezerwacje, ponieważ nie mamy jednego systemu."),
]


@pytest.mark.parametrize("lang,text", PROBLEM, ids=[lang for lang, _ in PROBLEM])
def test_problem_statement_passes(lang, text):
    assert _status("problem-defined", text) == "pass"


SOLUTION_FIRST = [
    ("it", "Vogliamo un sito web nuovo."),
    ("de", "Wir wollen eine neue Plattform."),
    ("fr", "Nous voulons une plateforme."),
    ("es", "Queremos una plataforma."),
    ("nl", "Wij willen een website."),
    ("pl", "Chcemy platforma."),
]


@pytest.mark.parametrize("lang,text", SOLUTION_FIRST, ids=[lang for lang, _ in SOLUTION_FIRST])
def test_solution_first_fails(lang, text):
    assert _status("problem-defined", text) == "fail"


def test_italian_esclusivamente_is_not_a_boundary():
    """'esclusivamente' contains the stem 'esclusi'; it names no exclusion."""
    rules, _ = load_bundled()
    text = (
        "# Prenotazioni\n\nL'obiettivo è esclusivamente la pianificazione dei "
        "coperti totali. Vogliamo una vista unica del giorno."
    )
    verdict = MockJudge().judge(rules["scope-boundaries"], text, "brief")
    assert verdict.status.value == "fail"


def test_italian_spelled_exclusion_is_a_boundary():
    rules, _ = load_bundled()
    text = "# Prenotazioni\n\nLa cassa del ristorante e la fatturazione sono escluse."
    verdict = MockJudge().judge(rules["scope-boundaries"], text, "brief")
    assert verdict.status.value == "pass"
