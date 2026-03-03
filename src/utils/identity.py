import secrets
import string

def gen_password(n=24) -> str:
    """
    Generate a random password to create a cloudstack user.\n
    This is necessary because the API requires a password to be inputed, 
    but we won't use this password for anything, since the auth is done via SAML SSO. 
    The password is only used to satisfy the API requirement.

    Args:
        n (int, optional): Number of characters in the password. Defaults to 24.

    Returns:
        str: The generated random password.
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*_-"
    return "".join(secrets.choice(alphabet) for _ in range(n))

def gen_username(email: str) -> str:
    """
    Generate a username from an email address by taking the part 
    before the "@" symbol and converting it to lowercase."

    Args:
        email (str): The email address to generate the username from.

    Returns:
        str: The extracted username.
    """
    return email.split("@", 1)[0].lower()