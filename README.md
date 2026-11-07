# État du service LION CONNECT / LION CONNECT service status

Page publique : https://status.lion-connect.com

- `status.json` : état signé (Ed25519, clé dédiée), publié par la surveillance automatique (`.github/workflows/monitor.yml`),
  qui teste lion-connect.com toutes les 5 minutes depuis GitHub. L'application LION CONNECT le lit pour savoir si une panne
  vient de notre côté.
- `message.json` : message facultatif affiché sur la page (modifiable à la main ; il est signé au passage suivant).

Public status page and signed status file of the LION CONNECT service.
