from turtle import update

from config.logging import setup_logging
from services.cloudstack_service import get_cloudstack

# ✅ Importar e setup logging PRIMEIRO
setup_logging()  # ou "INFO" em produção

cs = get_cloudstack()

print(cs.get_account(account_id="13be4938-bae9-4172-8a1e-e2000f895aa4"))
print(cs.update_account(account_id="13be4938-bae9-4172-8a1e-e2000f895aa4",  updates={"name": "Teste",}))
print(cs.update_account(account_id="13be4938-bae9-4172-8a1e-e2000f895aa4",  updates={"name": "fc56908",}))