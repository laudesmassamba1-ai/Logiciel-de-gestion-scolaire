
from repositories.base import RepositoryBase
from repositories.agenda_repository import AgendaRepository
from repositories.blocnote_repository import BlocNoteRepository
from repositories.classe_repository import ClasseRepository
from repositories.compte_repository import CompteRepository
from repositories.eleve_repository import EleveRepository
from repositories.finance_repository import FinanceRepository
from repositories.note_repository import NoteRepository
from repositories.parametre_repository import ParametreRepository
from repositories.pedagogie_repository import PedagogieRepository
from repositories.personnel_repository import PersonnelRepository
from repositories.planning_repository import PlanningRepository
from repositories.presence_repository import PresenceRepository


class _Repos:

    def __init__(self):
        self.agenda = AgendaRepository()
        self.blocnote = BlocNoteRepository()
        self.eleve = EleveRepository()
        self.classe = ClasseRepository()
        self.pedagogie = PedagogieRepository()
        self.finance = FinanceRepository()
        self.note = NoteRepository()
        self.personnel_repo = PersonnelRepository()
        self.compte = CompteRepository()
        self.planning = PlanningRepository()
        self.parametre = ParametreRepository()
        self.presence = PresenceRepository()
        self._depots = (
            self.agenda, self.blocnote, self.eleve, self.classe,
            self.pedagogie, self.finance, self.note,
            self.personnel_repo, self.compte, self.planning, self.parametre,
            self.presence,
        )

    def presences(self, classe_id=None, date=None):
        """Toutes les présences (sans filtre) ou pour une classe/date."""
        if classe_id is not None and date is not None:
            return self.presence.presences(classe_id, date)
        return self.presence.all_presences()

    def notes(self, utilisateur_id=None):
        """Notes du bloc-notes (requiert utilisateur_id)."""
        if utilisateur_id is None:
            from services.auth import AuthService
            user = AuthService().get_saved_user()
            utilisateur_id = user["id"] if user else None
        if utilisateur_id is None:
            return []
        return self.blocnote.notes(utilisateur_id)

    # --- Méthodes exposées explicitement (évite __getattr__ ambigu) ---
    def planning_for(self, classe_id):
        return self.planning.planning_for(classe_id)

    def matiere_by_nom(self, nom):
        return self.pedagogie.matiere_by_nom(nom)

    def enseignant_par_matiere(self, matiere_id):
        return self.pedagogie.enseignant_par_matiere(matiere_id)

    def enseignant_by_id(self, pid):
        return self.personnel_repo.personnel_by_id(pid) if hasattr(self.personnel_repo, 'personnel_by_id') else None

    def solde_eleve(self, eleve_id, annee_scolaire=""):
        return self.finance.solde_eleve(eleve_id, annee_scolaire)

    def presences_statuts(self):
        return self.presence.presences_statuts()

    def classe_by_id(self, classe_id):
        return self.classe.classe_by_id(classe_id) if hasattr(self.classe, 'classe_by_id') else None


    def __getattr__(self, name):
        for depot in self._depots:
            if hasattr(depot, name):
                return getattr(depot, name)
        raise AttributeError(name)


repos = _Repos()
