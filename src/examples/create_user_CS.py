import secrets
import string
from models.models import RootModel
from cloudstack.cs_client import get_cs
from models.models import RootModel

STUDENT_ROLE_ID = "e7580ffb-8931-4dea-9659-481c7d1d7c71"
STUDENTS_DOMAIN_ID = "1488a55a-800b-472f-94d7-7273a00a1208"
IDP_ENTITY_ID = "https://10.10.5.52:8443/realms/Cloud-DI"

def gen_password(n: int = 24):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*_-"
    return "".join(secrets.choice(alphabet) for _ in range(n))

def create_student_user(email: str, firstname: str, lastname: str):
    cs = get_cs()

    username = email.split("@", 1)[0].lower()
    password = gen_password()

    # 1) createAccount cria account + user inicial
    resp = cs.createAccount(
        account=username,
        username=username,
        email=email,
        firstname=firstname,
        lastname=lastname,
        password=password,
        domainid=STUDENTS_DOMAIN_ID,
        accounttype="0",
    )

    model = RootModel(**resp)

    user = model.account.user
    user_id = user.id
    account_id = model.account.id

    # 2) autorizar SAML para este user
    # (se a tua instalação exigir entityid explícito, mantém; caso contrário podes tirar)
    cs.authorizeSamlSso(userid=user_id, entityid=IDP_ENTITY_ID)

    # 3) aplicar role ao user (não é updateAccount)
    cs.updateUser(id=user_id, roleid=STUDENT_ROLE_ID)

    return {
        "username": username,
        "email": email,
        "account_id": account_id,
        "user_id": user_id,
        "generated_password": password, 
        "raw_response": resp,
    }