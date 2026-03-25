from turtle import update

from config.logging import setup_logging
from services.cloudstack_service import get_cloudstack

# ✅ Importar e setup logging PRIMEIRO
setup_logging()  # ou "INFO" em produção

cs = get_cloudstack()

print(cs.duplicate_role("4eff4f67-dff5-4179-bba8-802d9c7163cc", "Student"))