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
        # UUID genere UNE SEULE fois et conserve sur l'objet : deux appels
        # successifs doivent renvoyer le meme identifiant.
        if not self.uuid_client:
            self.uuid_client = str(_uuid.uuid4())
        d["uuid_client"] = self.uuid_client
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
