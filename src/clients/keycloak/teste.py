from ks2cs.logging_conf import setup_logging
from services.keycloak_service import get_keycloak
from services.cloudstack_service import get_cloudstack
from utils.identity import gen_password

# ✅ Importar e setup logging PRIMEIRO
setup_logging()  # ou "INFO" em produção

kc = get_keycloak()
cs = get_cloudstack()

username = "fc56908"
email = "fc56908@alunos.fc.ul.pt"
firstname = "joao"
lastname = "oliveira"
password = gen_password()

kc_user = kc.create_user({
    "username": username,
    "email": email,
    "firstName": firstname,
    "lastName": lastname,
    "enabled": True
})
cs_user = cs.create_account(username, username, email, firstname=firstname, lastname=lastname, password=password)

print("KC user:", kc_user)
print("CS user:", cs_user)