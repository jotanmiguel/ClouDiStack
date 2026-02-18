from cs import CloudStack
import json
from examples.models import RootModel

cs = CloudStack(
    endpoint="http://10.10.5.52:8080/client/api",
    key="5VRUsYejS6eji7AOFM-pbiZlu-i9aIXoEvHUdN1onimGL5vcC1zp1X1HDcrQjvbl47k96hA-7z1c8c3V6Re6tg",
    secret="YBW-Cl8CJZnTJp14laXW0zvArfso-YHfwoq6fBNI9HWZ5SuBYv6KLE97A4lNlq6lpzt_mPUFCdDzFa6ZhyqSqA",
)

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

print("Raw response:")
print(account)

model = RootModel(**account)

cs.authorizeSamlSso(enable=True, userid=model.account.user.id, entityid="https://10.10.5.52:8443/realms/Cloud-DI")

cs.updateUser(
    id=model.account.user.id,
    roleid="e7580ffb-8931-4dea-9659-481c7d1d7c71"
)

print("Created account:")
print(account)
