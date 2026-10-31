# Контракты проверки подключений Channels

Синтетические ответы без рабочих credentials и данных магазинов:

- `prom-groups.json`: `groups/list`, единственная корневая группа как identity.
- `rozetka-login.json`: `GET /sites/get-auth-data` с API-токеном; identity —
  `content.market.id`. Историческое имя fixture не означает парольную авторизацию.
- `woocommerce-system-status.json`: canonical `environment.site_url`.

Fixtures проверяют обработку ответа verifier и не заменяют проверку живого API.
