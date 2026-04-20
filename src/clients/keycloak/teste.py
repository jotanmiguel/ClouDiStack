from time import sleep

from pandas import Timestamp
from ks2cs.logging_conf import setup_logging
from services.keycloak_service import get_keycloak

# ✅ Importar e setup logging PRIMEIRO
setup_logging()  # ou "INFO" em produção

kc = get_keycloak()

user_id = kc.create_user({
    "username": "testuser",
    "email": "testuser@example.com",
    "firstName": "Test",
    "lastName": "User"
})

sleep(100)

kc.delete_user(user_id)