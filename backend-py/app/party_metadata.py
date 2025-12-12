"""
Metadata de partidos políticos y candidatos para elecciones Costa Rica 2026.
Generado automáticamente desde los datos del TSE.
"""

from typing import TypedDict


class PartyMetadata(TypedDict):
    abbreviation: str
    name: str
    candidate: str
    site: str
    plan: str


# Metadata completa de todos los partidos
PARTIES_METADATA: list[PartyMetadata] = [
    {
        "abbreviation": "ACRM",
        "name": "Aquí Costa Rica Manda",
        "candidate": "Ronny Castillo González",
        "site": "https://www.tse.go.cr/fichas/candidaturas/P/p-ACRM",
        "plan": "ACRM.pdf",
    },
    {
        "abbreviation": "CAC",
        "name": "Coalición Agenda Ciudadana",
        "candidate": "Claudia Dobles Camargo",
        "site": "https://www.tse.go.cr/fichas/candidaturas/P/p-CAC",
        "plan": "CAC.pdf",
    },
    {
        "abbreviation": "CDS",
        "name": "Centro Democrático y Social",
        "candidate": "Ana Virginia Calzada",
        "site": "https://www.tse.go.cr/fichas/candidaturas/P/p-CDS",
        "plan": "CDS.pdf",
    },
    {
        "abbreviation": "CR1",
        "name": "Costa Rica Primero",
        "candidate": "Douglas Caamaño Quirós",
        "site": "https://www.tse.go.cr/fichas/candidaturas/P/p-CR1",
        "plan": "CR1.pdf",
    },
    {
        "abbreviation": "FA",
        "name": "Frente Amplio",
        "candidate": "Ariel Robles Barrantes",
        "site": "https://www.tse.go.cr/fichas/candidaturas/P/p-FA",
        "plan": "FA.pdf",
    },
    {
        "abbreviation": "PA",
        "name": "Partido Avanza",
        "candidate": "Jose Aguilar Berrocal",
        "site": "https://www.tse.go.cr/fichas/candidaturas/P/p-PA",
        "plan": "PA.pdf",
    },
    {
        "abbreviation": "PDLCT",
        "name": "Partido de la Clase Trabajadora",
        "candidate": "David Hernández Brenes",
        "site": "https://www.tse.go.cr/fichas/candidaturas/P/p-PDLCT",
        "plan": "PDLCT.pdf",
    },
    {
        "abbreviation": "PEL",
        "name": "Partido Esperanza y Libertad",
        "candidate": "Marco Rodríguez Badilla",
        "site": "https://www.tse.go.cr/fichas/candidaturas/P/p-PEL",
        "plan": "PEL.pdf",
    },
    {
        "abbreviation": "PEN",
        "name": "Partido Esperanza Nacional",
        "candidate": "Claudio Alpízar Otoya",
        "site": "https://www.tse.go.cr/fichas/candidaturas/P/p-PEN",
        "plan": "PEN.pdf",
    },
    {
        "abbreviation": "PIN",
        "name": "Partido Integración Nacional",
        "candidate": "Luis Amador Jiménez",
        "site": "https://www.tse.go.cr/fichas/candidaturas/P/p-PIN",
        "plan": "PIN.pdf",
    },
    {
        "abbreviation": "PJSC",
        "name": "Partido Justicia Social Costarricense",
        "candidate": "Walter Rubén Hernández Juárez",
        "site": "https://www.tse.go.cr/fichas/candidaturas/P/p-PJSC",
        "plan": "PJSC.pdf",
    },
    {
        "abbreviation": "PLN",
        "name": "Partido Liberación Nacional",
        "candidate": "Álvaro Ramos Chaves",
        "site": "https://www.tse.go.cr/fichas/candidaturas/P/p-PLN",
        "plan": "PLN.pdf",
    },
    {
        "abbreviation": "PLP",
        "name": "Partido Liberal Progresista",
        "candidate": "Eliecer Feinzaig Mintz",
        "site": "https://www.tse.go.cr/fichas/candidaturas/P/p-PLP",
        "plan": "PLP.pdf",
    },
    {
        "abbreviation": "PNG",
        "name": "Partido Nueva Generación",
        "candidate": "Fernando Zamora Castellanos",
        "site": "https://www.tse.go.cr/fichas/candidaturas/P/p-PNG",
        "plan": "PNG.pdf",
    },
    {
        "abbreviation": "PNR",
        "name": "Partido Nueva República",
        "candidate": "Fabricio Alvarado Muñoz",
        "site": "https://www.tse.go.cr/fichas/candidaturas/P/p-PNR",
        "plan": "PNR.pdf",
    },
    {
        "abbreviation": "PPSO",
        "name": "Partido Pueblo Soberano",
        "candidate": "Laura Fernández Delgado",
        "site": "https://www.tse.go.cr/fichas/candidaturas/P/p-PPSO",
        "plan": "PPSO.pdf",
    },
    {
        "abbreviation": "PSD",
        "name": "Partido Progreso Social Democrático",
        "candidate": "Luz Mary Alpízar Loaiza",
        "site": "https://www.tse.go.cr/fichas/candidaturas/P/p-PSD",
        "plan": "PSD.pdf",
    },
    {
        "abbreviation": "PUCD",
        "name": "Partido Unión Costarricense Democrática",
        "candidate": "Boris Molina Acevedo",
        "site": "https://www.tse.go.cr/fichas/candidaturas/P/p-PUCD",
        "plan": "PUCD.pdf",
    },
    {
        "abbreviation": "PUSC",
        "name": "Partido Unidad Social Cristiana",
        "candidate": "Juan Carlos Hidalgo Bogantes",
        "site": "https://www.tse.go.cr/fichas/candidaturas/P/p-PUSC",
        "plan": "PUSC.pdf",
    },
    {
        "abbreviation": "UP",
        "name": "Unidos Podemos",
        "candidate": "Natalia Díaz Quintana",
        "site": "https://www.tse.go.cr/fichas/candidaturas/P/p-UP",
        "plan": "UP.pdf",
    },
]

# Mapeos útiles para búsquedas rápidas
CANDIDATE_TO_PARTY = {party["candidate"]: party["abbreviation"] for party in PARTIES_METADATA}

PARTY_NAME_TO_ABBR = {party["name"]: party["abbreviation"] for party in PARTIES_METADATA}

# Diccionario completo por sigla
PARTIES_BY_ABBR = {party["abbreviation"]: party for party in PARTIES_METADATA}


def get_party_by_candidate(candidate_name: str) -> str | None:
    """Get party abbreviation from candidate name."""
    return CANDIDATE_TO_PARTY.get(candidate_name)


def get_party_by_name(party_name: str) -> str | None:
    """Get party abbreviation from full party name."""
    return PARTY_NAME_TO_ABBR.get(party_name)


def get_party_metadata(abbreviation: str) -> PartyMetadata | None:
    """Get complete metadata for a party by abbreviation."""
    return PARTIES_BY_ABBR.get(abbreviation)
