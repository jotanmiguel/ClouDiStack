from config.logging import setup_logging
from services.cloudstack_service import get_cloudstack

# ✅ Importar e setup logging PRIMEIRO
setup_logging()  # ou "INFO" em produção

cs = get_cloudstack()

print(cs.list_accounts())