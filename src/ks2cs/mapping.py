from dataclasses import dataclass

@dataclass(frozen=True)
class ProvisioningDecision:
    account_name: str
    role: str  # ex: "student" | "staff"

def decide_role_from_email(email: str) -> str:
    dom = email.split("@", 1)[1].lower().strip()
    match dom:
        case "alunos.fc.ul.pt":
            return "student"
        case "di.fc.ul.pt":
            return "staff"
    
    return "student"

def decide_account_name(username: str, email: str) -> str:
    # Ajusta aqui a convenção do DI
    return username or email