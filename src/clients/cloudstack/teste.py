from config.logging import setup_logging
from services.cloudstack_service import get_cloudstack

# ✅ Importar e setup logging PRIMEIRO
setup_logging()  # ou "INFO" em produção

cs = get_cloudstack()

print(cs.list_all_resource_limits())
print(cs.update_cpu_resource_limit(account="teste", domain="afc17197-31bd-11f1-8f49-cec6e5fcc99e", max=1))
print(cs.update_ip_resource_limit(account="teste", domain="afc17197-31bd-11f1-8f49-cec6e5fcc99e", max=1))
print(cs.update_volume_resource_limit(account="teste", domain="afc17197-31bd-11f1-8f49-cec6e5fcc99e", max=1))
print(cs.update_vm_resource_limit(account="teste", domain="afc17197-31bd-11f1-8f49-cec6e5fcc99e", max=1))
print(cs.update_memory_resource_limit(account="teste", domain="afc17197-31bd-11f1-8f49-cec6e5fcc99e", max=1))
print(cs.update_network_resource_limit(account="teste", domain="afc17197-31bd-11f1-8f49-cec6e5fcc99e", max=1))
print(cs.update_primary_storage_resource_limit(account="teste", domain="afc17197-31bd-11f1-8f49-cec6e5fcc99e", max=1))
print(cs.update_secondary_storage_resource_limit(account="teste", domain="afc17197-31bd-11f1-8f49-cec6e5fcc99e", max=1))
print(cs.update_snapshot_resource_limit(account="teste", domain="afc17197-31bd-11f1-8f49-cec6e5fcc99e", max=1))
print(cs.list_all_resource_limits())