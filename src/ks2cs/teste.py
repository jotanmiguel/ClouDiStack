from pydoc import cli

from keycloak import KeycloakAdmin, KeycloakOpenIDConnection

from ks2cs import keycloak_client

client = keycloak_client.KeycloakClient(
    server_url="https://10.10.5.52:8443/",
    username='admin',
    password='admin123',
    auth_realm="master",
    verify_tls=False,
    target_realm="Cloud-DI",
    client_id="admin-cli",
)

print(client.get_admin_events())
