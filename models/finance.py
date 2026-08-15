from dataclasses import asdict, dataclass, field


@dataclass
class TarifScolarite:
    classe_id: int = None
    type_frais: str = ""
    montant: float = 0.0
    annee_scolaire: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class Paiement:
    inscription_id: int = None
    eleve_id: int = None
    montant: float = 0.0
    mode_reglement: str = ""
    type_frais: str = ""
    date_paiement: str = ""
    annee_scolaire: str = ""
    trimestre: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class Solde:
    total_a_payer: float = 0.0
    total_paye: float = 0.0
    solde: float = 0.0

    def to_dict(self):
        return asdict(self)


@dataclass
class SuiviMensuel:
    mois: str = ""
    attendu: float = 0.0
    paye: float = 0.0

    def to_dict(self):
        return asdict(self)


@dataclass
class Bilan:
    total: float = 0.0
    paiements: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)
