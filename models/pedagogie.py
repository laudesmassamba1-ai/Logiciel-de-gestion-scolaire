from dataclasses import asdict, dataclass


@dataclass
class Enseignant:
    nom_complet: str = ""
    fonction: str = ""
    telephone: str = ""
    email: str = ""
    salaire: float = 0.0
    statut: str = "Contrat"

    def to_dict(self):
        return asdict(self)


@dataclass
class Matiere:
    nom: str = ""
    coefficient: float = 1.0

    def to_dict(self):
        return asdict(self)


@dataclass
class Programme:
    classe_id: int = None
    matiere_id: int = None
    enseignant_id: int = None
    coefficient: float = 1.0

    def to_dict(self):
        return asdict(self)
