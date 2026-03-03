from cloudstack.cs_client import get_cs
from services.roles import duplicate_role


cs = get_cs()

duplicate_role(cs, source_role_name="User", new_role_name="StudentRole")