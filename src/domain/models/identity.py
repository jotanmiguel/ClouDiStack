from dataclasses import dataclass

@dataclass(frozen=True)
class UserInput:
    email: str
    firstname: str
    lastname: str
    groups: list[str]

@dataclass(frozen=True)
class GroupProfile:
    domain_id: str
    role_id: str
    is_student: bool