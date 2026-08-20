import uuid as _uuid
from dataclasses import asdict, dataclass


@dataclass
class Eleve:
    matricule: str = ""
    nom: str = ""
    prenom: str = ""
    sexe: str = ""
    date_naissance: str = ""
    lieu_naissance: str = ""
    classe_id: int = None
    ecole_provenance: str = ""
    pere_nom: str = ""
    pere_tel: str = ""
    mere_nom: str = ""
    mere_tel: str = ""
    tuteur_nom: str = ""
    tuteur_tel: str = ""
    adresse: str = ""
    redoublant: int = 0
    check_acte: int = 0
    check_photos: int = 0
    check_bulletin: int = 0
    statut: str = "Inscrit"
    date_inscription: str = ""
    uuid_client: str = ""

    def to_dict(self):
        d = asdict(self)
        if not d["uuid_client"]:
            d["uuid_client"] = str(_uuid.uuid4())
        return d


@dataclass
class PaiementInscription:
    montant: float = 0.0
    mode_reglement: str = ""
    date_paiement: str = ""
    annee_scolaire: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class BodyAjouterEleve:
    eleve: Eleve = None
    paiement: PaiementInscription = None

    def to_dict(self):
        return {
            "eleve": self.eleve.to_dict() if self.eleve else None,
            "paiement": self.paiement.to_dict() if self.paiement else None,
        }


@dataclass
class Parent:
    nom: str = ""
    prenom: str = ""
    telephone: str = ""
    lien: str = ""

    def to_dict(self):
        return asdict(self)
