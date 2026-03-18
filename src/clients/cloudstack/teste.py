from config.logging import setup_logging
from services.cloudstack_service import get_cloudstack

# ✅ Importar e setup logging PRIMEIRO
setup_logging()  # ou "INFO" em produção

cs = get_cloudstack()

cs.get_user("b1e5c8e7-9a3c-4d0b-9f1a-2c3d4e5f6a7b")
