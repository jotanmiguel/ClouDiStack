from services.keycloak_service import get_keycloak
from services.cloudstack_service import get_cloudstack

ks = get_keycloak()
cs = get_cloudstack()


# ==============================
# RUN TEST
# ==============================

def run_test():
    resources = cs.list_all_resource_limits()
    print(resources)


if __name__ == "__main__":
    run_test()