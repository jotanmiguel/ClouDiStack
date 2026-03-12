from cloudi.user_ops import get_all_accounts
from services.keycloak_service import get_keycloak
from cloudstack.cs_client import get_cs

cs = get_cs()
kc = get_keycloak()

keycloak_users = kc.get_users()
clodstack_users = get_all_accounts(cs)

print("Keycloak users:")
for user in keycloak_users:
    print(user)

print("\nCloudStack users:")
for user in clodstack_users:
    print(user)