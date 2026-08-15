from dataclasses import asdict, dataclass


@dataclass
class Classe:
    nom: str = ""
    niveau: str = ""
    capacite: int = 50
    salle: str = ""
    titulaire: str = ""
    cycle_id: int = None

    def to_dict(self):
        return asdict(self)


@dataclass
class Cycle:
    nom: str = ""
    description: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class AnneeScolaire:
    libelle: str = ""
    date_debut: str = ""
    date_fin: str = ""
    est_active: bool = False

    def to_dict(self):
        return asdict(self)
