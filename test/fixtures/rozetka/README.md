# Rozetka Read fixtures

`read.json` — синтетическая карточка на основе структуры официального Seller API,
включая пример `GET /goods/details` с массивом `content.item`.
Источник: https://api-seller.rozetka.com.ua/apidoc/#api-ApiItems-GetGoodsItemDetails
Проверено 2026-10-07. Это не ответ реального кабинета и не подтверждение прав,
rate limits или полноты выдачи площадки. ID, URLs и контент служат тестовыми данными.
Добавлены скидка, нулевой остаток, false, неизвестное поле и небезопасный HTML для
проверки сохранения native данных и нормализации Read документа.
