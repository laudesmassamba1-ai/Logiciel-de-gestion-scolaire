# instance partagee des depots : tout le projet l'utilise pour lire/ecrire
from repositories.base import RepositoryBase
from repositories.classe_repository import ClasseRepository
from repositories.compte_repository import CompteRepository
from repositories.eleve_repository import EleveRepository
from repositories.finance_repository import FinanceRepository
from repositories.note_repository import NoteRepository
from repositories.parametre_repository import ParametreRepository
from repositories.pedagogie_repository import PedagogieRepository
from repositories.personnel_repository import PersonnelRepository
from repositories.planning_repository import PlanningRepository


class _Repos:
    # regroupe tous les depots derriere une seule facade
    def __init__(self):
        self.eleve = EleveRepository()
        self.classe = ClasseRepository()
        self.pedagogie = PedagogieRepository()
        self.finance = FinanceRepository()
        self.note = NoteRepository()
        self.personnel_repo = PersonnelRepository()
        self.compte = CompteRepository()
        self.planning = PlanningRepository()
        self.parametre = ParametreRepository()
        self._depots = (
            self.eleve, self.classe, self.pedagogie, self.finance, self.note,
            self.personnel_repo, self.compte, self.planning, self.parametre,
        )

    # fait passer les appels (ex: repos.eleves()) vers le bon depot
    def __getattr__(self, name):
        for depot in self._depots:
            if hasattr(depot, name):
                return getattr(depot, name)
        raise AttributeError(name)


repos = _Repos()
