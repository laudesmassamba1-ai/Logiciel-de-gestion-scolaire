from services.auth import AuthService


# Instance unique du service d'authentification.
# NB : ne pas nommer cette variable "auth" : cela masquerait le module
# services.auth et rendrait AuthService inaccessible via le paquet.
auth_service = AuthService()
