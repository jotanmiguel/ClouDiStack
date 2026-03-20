# ClouDiStack

[text](https://cloudstack.apache.org/api/apidocs-4.22/)

# ClouDiStack — Webhook Dev Setup

## Pré-requisitos

- Python 3.11+
- [ngrok](https://ngrok.com/download) instalado
- CloudStack e Keycloak acessíveis
- `.env` configurado (ver `.env.example`)

---

## 1. Configurar o `.env`

Copia o exemplo e preenche:

```bash
cp .env.example .env
```

Campos obrigatórios:

```env
# CloudStack
CS_ENDPOINT=http://<cloudstack-host>:8080/client/api
CS_KEY=<api-key>
CS_SECRET=<secret-key>

# Keycloak
KC_SERVER_URL=https://<keycloak-host>:8443/
KC_REALM=master
KC_REALM_NAME=Cloud-DI
KC_CLIENT_ID=admin-cli
KC_USERNAME=admin
KC_PASSWORD=<password>
KC_VERIFY_TLS=false
```

---

## 2. Instalar dependências

```bash
pip install -r requirements.txt
```

---

## 3. Iniciar o webhook

```bash
cd src
uvicorn webhook:app --host 0.0.0.0 --port 5000 --reload
```

Confirma que está a correr:

```bash
curl http://localhost:5000/health
# {"status":"ok","kc":true,"cs":true}
```

---

## 4. Expor com ngrok

Noutro terminal:

```bash
ngrok http 5000
```

Copia o URL público — algo como:

```
https://abc123.ngrok.io
```

---

## 5. Registar o webhook no Keycloak

Com o script Python:

```bash
cd src
python -c "
from webhooks.client import WebhookClient
import os
from dotenv import load_dotenv

load_dotenv('../.env')

wc = WebhookClient(
    base_url=os.getenv('KC_SERVER_URL'),
    realm=os.getenv('KC_REALM_NAME'),
    admin_user=os.getenv('KC_USERNAME'),
    verify_ssl=False,
)
wc.authenticate(os.getenv('KC_PASSWORD'))
result = wc.create(
    url='https://<ngrok-url>/webhook/keycloak',
    secret='dev-secret',
    event_types=['*'],
)
print('Criado:', result)
print('Ativos:', wc.list())
"
```

Ou via CLI:

```bash
python -m src.webhooks.cli -p <password> create \
  --url https://<ngrok-url>/webhook/keycloak \
  --secret dev-secret
```

Confirma:

```bash
python -m src.webhooks.cli -p <password> list
```

---

## 6. Testar

Cria um utilizador no Keycloak Admin Console e verifica os logs do webhook:

```
📥 type=UNKNOWN resourceType=USER operationType=CREATE realm=Cloud-DI
✅ Criado: joao (joao@alunos.fc.ul.pt) role=student
```

---

## Notas

- O URL do ngrok **muda a cada reinício** (conta free). Quando mudar, repete o passo 5.
- Para apagar o webhook antigo antes de recriar:
  ```bash
  python -m src.webhooks.cli -p <password> list   # copia o id
  python -m src.webhooks.cli -p <password> delete --id <id>
  ```
- Para ver o histórico de eventos enviados pelo Keycloak:
  ```bash
  python -m src.webhooks.cli -p <password> sends --id <webhook-id>
  ```