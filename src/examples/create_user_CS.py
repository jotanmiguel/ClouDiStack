from cs import CloudStack
import json
from examples.models import RootModel
from main import get_cs

cs = get_cs()

account = cs.createAccount(
    account="joao",
    username="joao",
    email="joao@alunos.fc.ul.pt",
    firstname="joao",
    lastname="Student",
    password="admin123",
    domainid="1488a55a-800b-472f-94d7-7273a00a1208",
    accounttype="0",
)

model = RootModel(**account)

cs.authorizeSamlSso(enable=True, userid=model.account.user.id, entityid="https://10.10.5.52:8443/realms/Cloud-DI")

cs.updateAccount(
    id=model.account.user.id,
    roleid="e7580ffb-8931-4dea-9659-481c7d1d7c71"
)

print("Created account:")
print(account)
