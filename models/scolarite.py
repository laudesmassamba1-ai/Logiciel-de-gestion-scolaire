from dataclasses import asdict, dataclass, field


@dataclass
class Note:
    eleve_id: int = None
    matiere_id: int = None
    periode: str = ""
    devoir1: float = None
    devoir2: float = None
    composition: float = None

    def to_dict(self):
        return asdict(self)


@dataclass
class Moyenne:
    nom: str = ""
    prenom: str = ""
    type_evaluation: str = ""
    valeur: float = 0.0

    def to_dict(self):
        return asdict(self)


@dataclass
class Bulletin:
    nom: str = ""
    prenom: str = ""
    trimestre: str = ""
    moyennes: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass
class Presence:
    eleve_id: int = None
    classe_id: int = None
    date: str = ""
    statut: str = "Present"
    motif: str = ""

    def to_dict(self):
        return asdict(self)
