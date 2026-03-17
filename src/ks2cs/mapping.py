from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, List, Any

@dataclass(frozen=True)
class ProvisioningDecision:
    account_name: str
    role: str
    tier: str
    domain_id: str
    role_id: str
    custom_config: Dict[str, Any]

# CloudStack Roles Mapping (SERÁ PREENCHIDO NO DIA 4)
# Por enquanto, values placeholder
ROLES_MAPPING = {
    "students": {
        "role_name": "student",
        "domain_name": "alunos",
        "default_tier": "standard",
    },
    "staff": {
        "role_name": "staff",
        "domain_name": "di",
        "default_tier": "standard",
    },
    "teachers": {
        "role_name": "teacher",
        "domain_name": "di",
        "default_tier": "standard",
    },
    "researchers": {
        "role_name": "researcher",
        "domain_name": "di",
        "default_tier": "advanced",
    },
    "guests": {
        "role_name": "guest",
        "domain_name": "guests",
        "default_tier": "standard",
    },
}


def _get_keycloak_groups(user: dict) -> List[str]:
    """
    Extrai lista de grupos do user Keycloak.
    
    Keycloak armazena grupos como: ["/students", "/special_project"]
    Retorna: ["students", "special_project"]
    """
    groups = user.get("groups", [])
    
    # Remove leading slash
    groups = [g.lstrip("/") for g in groups]
    return groups


def _get_keycloak_attributes(user: dict) -> dict:
    """
    Extrai atributos customizados do user Keycloak.
    
    Keycloak guarda atributos como dict com valores em listas:
    {"cloudstack_tier": ["premium"], "custom_limits": ["20gb"]}
    
    Converte para dict simples:
    {"cloudstack_tier": "premium", "custom_limits": "20gb"}
    """
    attributes = user.get("attributes", {})
    
    clean_attrs = {}
    for key, val in attributes.items():
        if isinstance(val, list) and val:
            clean_attrs[key] = val[0]  # Pega primeiro valor
        else:
            clean_attrs[key] = val
    
    return clean_attrs


def decide_cloudstack_tier_from_keycloak(user: dict) -> str:
    """
    Decide CloudStack tier (standard, premium, advanced) baseado em Keycloak.
    
    Priority:
    1. Atributo 'cloudstack_tier' no user (se existe)
    2. Tier default do grupo principal
    3. Default: "standard"
    
    Args:
        user: User object do Keycloak
    
    Returns:
        str: "standard", "premium", ou "advanced"
    """
    attrs = _get_keycloak_attributes(user)
    
    # 1. Verificar se user tem tier explícito
    if "cloudstack_tier" in attrs:
        tier = attrs["cloudstack_tier"].lower()
        if tier in ["standard", "premium", "advanced"]:
            return tier
    
    # 2. Usar tier default do grupo
    groups = _get_keycloak_groups(user)
    for group in groups:
        if group in ROLES_MAPPING:
            return ROLES_MAPPING[group]["default_tier"]
    
    # 3. Default
    return "standard"


def decide_cloudstack_role_from_keycloak(user: dict) -> tuple[str, str, dict]:
    """
    Decide CloudStack role, domain, e custom config baseado em Keycloak user.
    
    Args:
        user: User object do Keycloak (com 'groups' e 'attributes')
    
    Returns:
        tuple: (role_name, domain_name, custom_config)
    
    Priority de grupos:
    1. students
    2. staff
    3. teachers
    4. researchers
    5. guests
    Se nenhum encontrado → default = guest
    """
    groups = _get_keycloak_groups(user)
    attrs = _get_keycloak_attributes(user)
    tier = decide_cloudstack_tier_from_keycloak(user)
    
    # Ordem de prioridade (primeira match ganha)
    priority_order = ["students", "staff", "teachers", "researchers", "guests"]
    
    role_name = None
    domain_name = None
    
    # Encontra primeiro grupo que existe em ROLES_MAPPING
    for priority_group in priority_order:
        if priority_group in groups:
            mapping = ROLES_MAPPING[priority_group]
            role_name = mapping["role_name"]
            domain_name = mapping["domain_name"]
            break
    
    # Se nenhum grupo encontrado, default = guest
    if not role_name:
        role_name = "guest"
        domain_name = "guests"
    
    # Montar custom config (será usado para validações e limites)
    custom_config = {
        "tier": tier,
        "groups": groups,
        "custom_limits": attrs.get("custom_limits", ""),
        "approved_resources": attrs.get("approved_resources", "").split(",") 
            if attrs.get("approved_resources") else [],
        "account_tier_suffix": f"_{tier}" if tier != "standard" else "",
    }
    
    return role_name, domain_name, custom_config


def decide_role_from_email(email: str) -> str:
    """
    DEPRECATED: Use decide_cloudstack_role_from_keycloak() instead.
    
    Mantido para backward compatibility.
    Decides role baseado apenas em email (fallback).
    
    Args:
        email (str): The email of the user.

    Returns:
        str: role name ("student" ou "staff").
    """
    dom = email.split("@", 1)[1].lower().strip()
    match dom:
        case "alunos.fc.ul.pt":
            return "student"
        case "di.fc.ul.pt":
            return "staff"
    
    return "student"  # Default


def decide_account_name(username: str, email: str) -> str:
    """Generate account name from username or email."""
    return username or email


if __name__ == "__main__":
    # ===== TESTE LOCAL =====
    # Exemplo 1: Student Standard
    user1 = {
        "id": "user-123",
        "username": "joao",
        "email": "joao@alunos.fc.ul.pt",
        "groups": ["/students"],
        "attributes": {}
    }
    
    print("=" * 60)
    print("TESTE 1: Student Standard")
    print("=" * 60)
    role, domain, config = decide_cloudstack_role_from_keycloak(user1)
    print(f"Role: {role}")
    print(f"Domain: {domain}")
    print(f"Tier: {config['tier']}")
    print(f"Config: {config}")
    
    # Exemplo 2: Student Premium
    user2 = {
        "id": "user-456",
        "username": "maria",
        "email": "maria@alunos.fc.ul.pt",
        "groups": ["/students", "/special_project"],
        "attributes": {
            "cloudstack_tier": ["premium"],
            "custom_limits": ["20gb_storage"],
            "approved_resources": ["lab_access,extra_cpu"]
        }
    }
    
    print("\n" + "=" * 60)
    print("TESTE 2: Student Premium + Custom Limits")
    print("=" * 60)
    role, domain, config = decide_cloudstack_role_from_keycloak(user2)
    print(f"Role: {role}")
    print(f"Domain: {domain}")
    print(f"Tier: {config['tier']}")
    print(f"Groups: {config['groups']}")
    print(f"Custom Limits: {config['custom_limits']}")
    print(f"Approved Resources: {config['approved_resources']}")
    
    # Exemplo 3: Researcher (advanced tier por default)
    user3 = {
        "id": "user-789",
        "username": "prof_silva",
        "email": "prof_silva@di.fc.ul.pt",
        "groups": ["/researchers"],
        "attributes": {}
    }
    
    print("\n" + "=" * 60)
    print("TESTE 3: Researcher (Advanced Tier Default)")
    print("=" * 60)
    role, domain, config = decide_cloudstack_role_from_keycloak(user3)
    print(f"Role: {role}")
    print(f"Domain: {domain}")
    print(f"Tier: {config['tier']}")
    
    # Exemplo 4: Nenhum grupo reconhecido (default = guest)
    user4 = {
        "id": "user-xyz",
        "username": "unknown",
        "email": "unknown@example.com",
        "groups": ["/unknown_group"],
        "attributes": {}
    }
    
    print("\n" + "=" * 60)
    print("TESTE 4: Unknown Group (Default = Guest)")
    print("=" * 60)
    role, domain, config = decide_cloudstack_role_from_keycloak(user4)
    print(f"Role: {role}")
    print(f"Domain: {domain}")
    print(f"Tier: {config['tier']}")