# src/test_policy.py
from config.logging import setup_logging
from services.cloudstack_service import get_cloudstack
from services.keycloak_service import get_keycloak

setup_logging()
kc = get_keycloak()
cs = get_cloudstack()

# Busca um user real
user = kc.get_user(user_id="97501eee-2738-429b-8b07-e1dd2482bfba")
print("User:", user)