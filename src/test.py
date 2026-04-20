from services.keycloak_service import get_keycloak

ks = get_keycloak()


# ==============================
# TEST DATA
# ==============================



def generate_users(n=10):
    users = []
    for i in range(1, n + 1):
        username = f"fc{i:05d}"
        users.append({
            "username": username,
            "email": f"{username}@alunos.fc.ul.pt",
            "firstName": "Test",
            "lastName": f"User{i}"
        })
    return users


def generate_users_with_duplicates():
    users = generate_users(10)

    # duplicados propositados
    users.append(users[2])  # fc00003
    users.append(users[5])  # fc00006

    return users


# ==============================
# RUN TEST
# ==============================

def run_test():
    users = generate_users_with_duplicates()

    print("=== START TEST ===\n")

    for user in users:
        ks.create_user(user)

    print("\n=== TEST FINISHED ===")


if __name__ == "__main__":
    run_test()