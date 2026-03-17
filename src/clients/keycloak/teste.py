from ks2cs.logging_conf import setup_logging
from services.keycloak_service import get_keycloak

# ✅ Importar e setup logging PRIMEIRO
setup_logging()  # ou "INFO" em produção

kc = get_keycloak()

print(kc.get_user("4cf2230f-edaf-4513-92c8-d637d8696ebf"))
print(kc.get_user_attributes("4cf2230f-edaf-4513-92c8-d637d8696ebf"))
print(kc.set_user_attributes("4cf2230f-edaf-4513-92c8-d637d8696ebf", {"cloudstackDomain": "value"}))
print(kc.get_user_attributes("4cf2230f-edaf-4513-92c8-d637d8696ebf"))