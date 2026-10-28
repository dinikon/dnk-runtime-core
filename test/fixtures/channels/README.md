# Контрактные примеры Channels

Синтетические минимальные fixtures по официальным формам ответов API; данные магазинов и рабочие credentials отсутствуют.

- Prom: https://public-api.docs.prom.ua/ — `groups/list`, `products/list`, `products/{id}`; поля `name_multilang`, `variation_base_id`, `variation_group_id`. Корневая группа — согласованный кандидат identity, стабильность которого на реальных магазинах ещё не подтверждена.
- Rozetka: https://api-seller.rozetka.com.ua/apidoc/ — Bearer API token, `GET /sites/get-auth-data`; `content.id` принадлежит пользователю, `content.market.id` — магазину. `/goods/all` и `/goods/archive` запрашиваются только с `page` и `pageSize`, без фильтра наличия; ответы содержат `_meta`, ключ `sync_source_id:price_offer_id`, необязательный `rz_item_id`. Историческое имя `rozetka-login.json` не означает парольную авторизацию.
- WooCommerce: https://developer.woocommerce.com/docs/apis/rest-api/v3/system-status — `environment.site_url`.
- WooCommerce products/variations: https://woocommerce.github.io/woocommerce-rest-api-docs/ — `type`, `manage_stock`, `stock_quantity`, `X-WP-TotalPages`; неподдерживаемые типы пропускаются, virtual/downloadable сохраняются.

Prom fixture намеренно содержит исходную USD при UAH канала: сумма сохраняется без конвертации. Отсутствующие переводы не подменяются. Неизвестные вложенные поля проверяют сохранение полного raw_data.

Эти fixtures проверяют код обработки контрактов и не заменяют live smoke проверку.
