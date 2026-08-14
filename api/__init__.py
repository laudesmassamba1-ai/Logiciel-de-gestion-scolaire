# client HTTP et filet de synchronisation avec le serveur
from api.client import ApiClient, ApiError, api_disponible

# instance partagee : tout le projet l'utilise pour parler au serveur
client = ApiClient()
