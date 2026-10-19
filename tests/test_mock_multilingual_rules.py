"""The offline judge reads every keyword rule in the Directory languages.

The welance.com editor scores live with this judge in twelve languages.
Before this, only the gate rules knew anything but English, so an Italian
brief with "tre mesi, prima dell'apertura di stagione" was told it had no
timeline. ar / zh-Hans / ja are left to the editor's on-demand real judge.
"""

import pytest

from brief_bar import load_bundled
from brief_bar.judge import MockJudge

RULES, _ = load_bundled()
JUDGE = MockJudge()


def status(rule_id: str, text: str) -> str:
    return JUDGE.judge(RULES[rule_id], text, "brief").status.value


TIMELINE = [
    ("it", "Tre mesi, pronti prima dell'apertura di stagione."),
    ("de", "Lieferung in drei Monaten, spätestens zum Saisonstart."),
    ("fr", "Trois mois, livré avant la saison."),
    ("es", "Tres meses, con un plazo antes de la temporada."),
    ("pt", "Três meses, com prazo até ao final do trimestre."),
    ("nl", "Drie maanden, uiterlijk voor het seizoen."),
    ("pl", "Trzy miesiące, do końca kwartału."),
]


@pytest.mark.parametrize(("lang", "text"), TIMELINE)
def test_timeline(lang, text):
    assert status("timeline", text) == "pass", lang


def test_timeline_absent_still_fails():
    assert status("timeline", "Vogliamo una vista unica delle prenotazioni.") == "fail"


def test_polish_termin_does_not_match_determine():
    assert status("timeline", "We need to determine the terminal setup.") == "fail"


@pytest.mark.parametrize(
    ("lang", "text"),
    [
        ("it", "Obiettivo: dimezzare il tempo di preventivo."),
        ("de", "Ziel: die Wartezeit senken."),
        ("fr", "Objectif : réduire les doubles réservations."),
        ("es", "Objetivo: reducir los conflictos."),
        ("pt", "Objetivo: reduzir os conflitos."),
        ("nl", "Doel: het aantal conflicten verminderen."),
        ("pl", "Cel: zmniejszyć liczbę konfliktów."),
    ],
)
def test_success_metrics(lang, text):
    assert status("success-metrics", text) == "pass", lang


@pytest.mark.parametrize(
    ("lang", "text"),
    [
        ("it", "Per chi è: le due persone alla reception."),
        ("de", "Zielgruppe: die Mitarbeiter am Empfang."),
        ("fr", "Pour qui : le personnel de la réception."),
        ("es", "Para quién: el personal de recepción."),
        ("pt", "Para quem: a equipa da receção."),
        ("nl", "Voor wie: de medewerkers aan de balie."),
        ("pl", "Dla kogo: pracownicy recepcji."),
    ],
)
def test_users_identified(lang, text):
    assert status("users-identified", text) == "pass", lang


@pytest.mark.parametrize(
    ("lang", "text"),
    [
        ("it", "Cerchiamo uno sviluppatore full stack."),
        ("de", "Wir suchen zwei Entwickler."),
        ("fr", "Nous cherchons un développeur."),
        ("es", "Buscamos un desarrollador."),
        ("pt", "Procuramos um programador."),
        ("nl", "We zoeken een ontwikkelaar."),
        ("pl", "Szukamy programisty."),
    ],
)
def test_team_shape(lang, text):
    assert status("team-shape", text) == "pass", lang


@pytest.mark.parametrize(
    ("lang", "text"),
    [
        ("it", "Vincoli tecnici: il gestionale camere ha un'interfaccia documentata."),
        ("de", "Die Schnittstelle zum bestehende System bleibt."),
        ("fr", "Contraintes techniques : intégration au système existant."),
        ("es", "Restricciones técnicas: integración con el sistema existente."),
        ("pt", "Restrições técnicas: integração com a base de dados atual."),
        ("nl", "Technische beperkingen: koppeling met het bestaande systeem."),
        ("pl", "Ograniczenia techniczne: integracja z istniejący system."),
    ],
)
def test_constraints_tech(lang, text):
    assert status("constraints-tech", text) == "pass", lang


@pytest.mark.parametrize(
    ("lang", "text"),
    [
        ("it", "Diamo per scontato che il gestionale risponda in tempo."),
        ("de", "Größtes Risiko: die Annahme, dass die Daten aktuell sind."),
        ("fr", "Hypothèse : le système répond à temps."),
        ("es", "Riesgo: depende de la API del proveedor."),
        ("pt", "Risco: a hipótese de que os dados estão atualizados."),
        ("nl", "Risico: de aanname dat de gegevens actueel zijn."),
        ("pl", "Ryzyko: założenie, że dane są aktualne."),
    ],
)
def test_assumptions_risks(lang, text):
    assert status("assumptions-risks", text) == "pass", lang


@pytest.mark.parametrize(
    ("lang", "text"),
    [
        ("it", "Trattiamo nomi e contatti degli ospiti; base giuridica documentata."),
        ("de", "Personenbezogene Daten der Gäste; Rechtsgrundlage nach DSGVO."),
        ("fr", "Données personnelles des clients ; base légale RGPD."),
        ("es", "Datos personales de los huéspedes; base jurídica RGPD."),
        ("pt", "Dados pessoais dos hóspedes; base legal RGPD."),
        ("nl", "Persoonsgegevens van gasten; rechtsgrond vastgelegd."),
        ("pl", "Dane osobowe gości; podstawa prawna udokumentowana."),
    ],
)
def test_data_compliance(lang, text):
    assert status("data-compliance", text) == "pass", lang


@pytest.mark.parametrize(
    ("lang", "text"),
    [
        ("es", "La página pública de reserva cumple accesibilidad AA."),
        ("pt", "A página pública cumpre acessibilidade AA."),
        ("de", "Die öffentliche Buchungsseite ist barrierefrei."),
        ("nl", "De openbare boekingspagina is toegankelijk."),
        ("pl", "Publiczna strona rezerwacji: dostępność AA."),
    ],
)
def test_accessibility(lang, text):
    assert status("accessibility-considered", text) == "pass", lang


def test_the_agriturismo_brief_reads_in_italian():
    """The real brief that exposed the gap, reduced to its sections."""
    text = (
        "# Prenotazioni e attività per un agriturismo con dodici camere\n\n"
        "## Il problema\nGestiamo tre agende separate e regolarmente qualcosa salta, "
        "perché nessuno vede tutto.\n\n"
        "## Per chi è\nLe due persone alla reception e il personale di sala.\n\n"
        "## Fuori perimetro\nLa cassa del ristorante. Non sostituiamo il gestionale camere.\n\n"
        "## Vincoli tecnici\nIl gestionale camere ha un'interfaccia documentata. "
        "La vista di domani deve funzionare anche offline.\n\n"
        "## Dati personali\nTrattiamo nomi e contatti. Servono base giuridica documentata "
        "e conservazione in UE.\n\n"
        "## Ipotesi e rischi\nDiamo per scontato che il gestionale esponga la disponibilità.\n\n"
        "## Come misuriamo il risultato\nAlmeno il 30% di richieste in più.\n\n"
        "## Budget e tempi\n30.000–45.000 €, tre mesi, pronti prima dell'apertura di stagione."
    )
    expected = {
        "clear-title": "pass",
        "problem-defined": "pass",
        "users-identified": "pass",
        "scope-boundaries": "pass",
        "constraints-tech": "pass",
        "data-compliance": "pass",
        "assumptions-risks": "pass",
        "success-metrics": "pass",
        "budget-floor": "pass",
        "timeline": "pass",
    }
    got = {rid: status(rid, text) for rid in expected}
    assert got == expected


@pytest.mark.parametrize(
    "text",
    [
        "Przetwarzamy dane osobowe pracowników, więc potrzebujemy podstawy prawnej.",
        "Dane osobowe: rejestr i okres retencji uzgodnimy z inspektorem ochrony danych.",
    ],
)
def test_polish_compliance_is_read_in_its_inflected_forms(text):
    assert status("data-compliance", text) == "pass"


@pytest.mark.parametrize(
    ("rule_id", "text", "expected"),
    [
        # each of these English words contains a new non-English entry as a
        # substring; none may change an English verdict
        ("timeline", "Keep the stock room free of moisture.", "fail"),
        ("success-metrics", "Only taxable items are listed.", "partial"),
        ("data-compliance", "The economics of the shop are simple.", "not_applicable"),
        ("assumptions-risks", "Our office is in San Francisco.", "fail"),
        ("accessibility-considered", "Staff confirm each reservation by phone.", "partial"),
    ],
)
def test_english_words_do_not_trip_the_new_vocabulary(rule_id, text, expected):
    assert status(rule_id, text) == expected
