from pandas import Timestamp
from ks2cs.logging_conf import setup_logging
from services.keycloak_service import get_keycloak

# ✅ Importar e setup logging PRIMEIRO
setup_logging()  # ou "INFO" em produção

kc = get_keycloak()

print(kc.get_user("634cfadd-7538-4b4a-90b5-28e5331f64e3"))
print(kc.set_user_attributes("634cfadd-7538-4b4a-90b5-28e5331f64e3", {"cloudstackRoleId": "7fd5d665-76f2-46a7-9a03-98e0a42985f8", "cloudstackSync": str(Timestamp.now().timestamp())}))