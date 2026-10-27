# Контрактные примеры Channels

Синтетические минимальные fixtures по официальным формам ответов API; данные магазинов и рабочие credentials отсутствуют.

- Prom: https://public-api.docs.prom.ua/ — `groups/list`. Единственная корневая группа является согласованным кандидатом identity, а не подтверждённой гарантией Prom. Проверка стабильности на реальных магазинах отложена.
- Rozetka: https://api-seller.rozetka.com.ua/apidoc/ — авторизация `sites`; `content.id` принадлежит пользователю, `content.market.id` — магазину.
- WooCommerce: https://developer.woocommerce.com/docs/apis/rest-api/v3/system-status — `environment.site_url`.

Эти fixtures проверяют код обработки контрактов и не заменяют live smoke проверку.
