# Files

Tenant-модуль приватного хранения. Реализация и границы: `docs/plan/files.md`.

[Файловый менеджер в Admin Console](../plan/files.md#следующий-этап-файловый-менеджер-в-admin-console)
реализован: список/поиск/пагинация по дискам, загрузка, корзина с восстановлением
и автоочисткой через 30 дней. Domain/persistence, API, worker/recovery и UI
срезы выполнены. Следующий этап — rollout и smoke test на отдельном tenant
с настоящим MinIO, session/CSRF и worker.

## Состояния файлов и корзина

`StoredFile` поддерживает `uploading → ready → trashed → purging → purged`.
Корзина хранит исходный объект под прежним ключом. `deleted_at`, `deleted_by`
и `purge_after` фиксируют удаление и срок ровно 720 часов в UTC; повторное
удаление не продлевает его. Восстановление возможно строго до срока и только
из `trashed`. В `purging` записаны `purge_requested_at` и `purge_job_id`;
подтверждение устаревшей job отклоняется. Замена job сохраняет даты корзины.

Write repository предоставляет `get_for_update` на сессии внешнего UoW:
ожидающий lock читает актуальную запись, включая refresh ранее загруженной ORM-модели.
`purged` используется только в Domain после подтверждения удаления storage;
затем `remove(aggregate)` удаляет SQL-запись в той же транзакции. Промежуточный
`save` состояния `purged` запрещён SQL-ограничением.

Tenant-миграция `0021_files_lifecycle` сохраняет старые записи и добавляет
поля/ограничения/индексы. Её downgrade блокирует таблицу перед проверкой и
отказывается терять записи `trashed`/`purging`. Применение к рабочим схемам
в рамках реализации не выполнялось.

Существующее внутреннее чтение и статистика дисков учитывают только `ready`.
Orphan cleanup защищает все зарегистрированные ключи, включая `trashed` и
`purging`. Изменение состояния через Console и физический per-file worker подключены.
Часовая проверка отправляет истёкшую корзину в очередь. Контракты и дальнейшая последовательность —
[в плане](../plan/files.md#выполненный-срез-1-domain-и-persistence).

## Конфигурация Instance

`DnkConfig.FILES` читает переменные проекта:

| Переменная | Назначение / default |
| --- | --- |
| FILES__ENDPOINT | обязательный host:port без scheme/path |
| FILES__ACCESS_KEY | обязательный secret |
| FILES__SECRET_KEY | обязательный secret |
| FILES__SECURE | TLS, true |
| FILES__REGION | optional, пустая строка |
| FILES__TIMEOUT_SECONDS | HTTP connect/read, 30; максимум 60 |
| FILES__OPERATION_TIMEOUT_SECONDS | передача файла, 600; максимум 600 |
| FILES__CONCURRENCY | число одновременных SDK операций, 4 |
| FILES__CONSOLE_MAX_UPLOAD_BYTES | максимальный размер одного файла в Console, 1073741824 (1 ГиБ), положительное число |

Нужны права на создание, tags, policy inspection, перечисление и удаление
бакетов/объектов/версий/multipart uploads в namespace `dnk-tenant-*`.
Этот namespace используется только Files. Пустой бакет без tags может быть
принят после незавершённого создания; непустой или чужой tagged-бакет отвергается.

Helm передаёт настройки через `application.files`. Access key и secret key
поддерживают `existingSecret` либо `value` по общему контракту secrets chart.
Внешний MinIO настраивается оператором: DNS, TLS и network isolation готовятся на Instance.
Для установки MinIO внутри релиза включите `minio.enabled=true`, задайте credentials
через `minio.auth.accessKey` / `minio.auth.secretKey` и размер PVC в
`minio.persistence.size`. Chart сам передаст backend и workers внутренний endpoint,
HTTP-режим и общие Secret references. `application.files` endpoint и credentials
в этом режиме оставьте пустыми. См. [пример values](../../helm/examples/values-minio.yaml)
и [описание установки](../../helm/README.md#внутренний-minio).
В Compose MinIO подключён к `file-storage` (`internal: true`); backend и workers
имеют доступ к этой сети по `minio:9000`. API и консоль опубликованы только на
`127.0.0.1`, порты задаются `MINIO_API_PORT` (9000) и `MINIO_CONSOLE_PORT` (9001).
Для публикации локальных портов MinIO дополнительно подключён к отдельной bridge
сети `file-storage-local`: Docker не публикует порты контейнера, подключённого
только к internal-сетям. Другие сервисы к локальной сети не подключаются.
Control Plane override отключает публикацию портов через `!reset []` и оставляет
MinIO только в `file-storage` через `!override [file-storage]`.
Для локального запуска backend используется `FILES__ENDPOINT=127.0.0.1:9000`
(либо выбранный API-порт) и `FILES__SECURE=false`. Значения `.env` в текущем
workspace не изменяются автоматически.

После изменения Compose пересоздайте только MinIO: `docker compose up -d minio`.
Проверка с хоста: `curl -f http://127.0.0.1:9000/minio/health/live` (либо выбранный
API-порт). Если `create_tenant.py` уже завершился ошибкой на подготовке хранилища,
tenant остаётся в статусе `provisioning`. Продолжите его создание командой
`dnk-manage files resume <tenant_uuid>`, вместо повторного создания tenant.

## Rollout и восстановление

1. Подготовить закрытый MinIO и настройки для backend, jobs и Control Plane worker.
2. Применить tenant-миграции: `dnk-manage tenant-migrations upgrade --all`.
3. Зарегистрировать и подготовить бакеты старых Tenant:
   `dnk-manage files prepare --all` либо `dnk-manage files prepare <tenant_uuid>`.
4. Перезапустить `dnk-manage jobs worker`: dispatcher должен обрабатывать
   `files.purge`, `files.trash.cleanup` и `files.trash.empty`; registrar запускается сразу и каждый час.
5. На отдельных тестовых файлах проверить API загрузки/корзины/восстановления/
   окончательного удаления. Admin UI относится к следующему срезу.

`files prepare` не меняет tenant status. `files resume <tenant_uuid>` продолжает
local onboarding и активирует Tenant после готовности бакета. Для Control Plane
Tenant повторная установка проходит штатным worker; local resume их отклоняет.
При ошибке CLI выводит tenant ID и тип ошибки без credentials и SDK response.

SQL downgrade не удаляет физические данные. Перед откатом миграции нужно
явно удалить tenant storage штатным процессом удаления Tenant либо сохранить
данные для восстановления. Нельзя удалять реестр, оставляя дальнейшую очистку
без координат бакетов.

## API Console

- `GET /api/console/files/providers/` → массив `id, name, kind, is_system`.
- `GET /api/console/files/buckets/?provider_id=<uuid>` → массив
  `id, provider_id, name, status, files_count, size_bytes`.
- `GET /api/console/files/items/` → `items, total, page, page_size`;
  список зарегистрированных файлов в состоянии `ready`.
- `GET /api/console/files/trash/` → отдельный контракт страницы корзины;
  состояния `trashed` и `purging`, даты удаления и срок восстановления.
- `GET /api/console/files/overview/` → количество и размер активных файлов,
  корзины, её части `purging` и четыре категории активных файлов.

Все пять endpoint требуют роль `admin` из trusted tenant principal и разрешение
authorization service `files.read` для `stored_file` без resource ID. Проверка
роли работает и с default allow-all adapter; отказ происходит до открытия UoW.
Credentials/config_ref, ключ объекта и purge job ID не входят в HTTP-контракт.
Файловый менеджер доступен администратору в «Модули → Файлы»
(`/admin/files`); вкладки «Корзина» и «Диски» имеют отдельные URL. Старый
`/files` перенаправляет с сохранением query. «Диски» показывают системный
default и только просмотр подключений. Объём — сумма зарегистрированных
размеров, а не физический disk usage MinIO.

### Массовые действия и очистка корзины

В обоих списках доступны выбор отдельных строк/карточек и «Все на странице».
Выбор относится к текущей странице и сбрасывается при смене tenant, вкладки,
фильтров или страницы. В активном списке можно перенести выбранные файлы в
корзину; в корзине — восстановить или удалить навсегда. `purging` не выбирается,
истёкшие файлы исключаются из восстановления, но могут удаляться навсегда.

Массовое действие открывает подтверждение со списком файлов. Запросы выполняются
последовательно через существующие admin/CSRF endpoints, по одной транзакции на
файл. Отображается результат каждого элемента; успешные элементы снимаются с
выделения и не входят в повтор. Конфликт отдельного файла не отменяет уже
успешные операции. Отказ доступа, rate limit, timeout и сетевой/server сбой
останавливают дальнейшую отправку. Повтор оставшихся файлов только ручной;
автоматического повтора нет. После пакета обновляются списки и сводка, ошибка
обновления не отменяет подтверждённое сервером действие. Смена tenant и unmount
отменяют запрос и не позволяют продолжить старую очередь.

`DELETE /api/console/files/trash/` без тела запускает очистку **всей** корзины
текущего tenant, независимо от UI search, category, bucket_id и пагинации.
Требуются trusted tenant admin, session-bound CSRF и `files.purge` для
`stored_file` с `resource_id=None`; разрешения на отдельный файл недостаточно.
Ответ `202 RequestTrashEmptyResponse` содержит `job_id` и UTC `cutoff`: запрос
сохранён, физическое удаление ещё не завершено. Кнопка «Очистить корзину» доступна
в корзине даже при пустой фильтрованной выдаче и требует отдельного подтверждения.
После принятия запроса открытая видимая вкладка обновляет список каждые 5 секунд,
включая период до появления первых `purging`; при пустой корзине, смене tenant,
вкладки или unmount этот дополнительный polling прекращается.

`RequestTrashEmptyHandler` сохраняет durable `files.trash.empty` в общем UoW.
Worker открывает собственный tenant gate/UoW и вызывает `EmptyTrashHandler` для
не более 100 ID по keyset, с исходным cutoff. Кандидаты — `trashed` с
`deleted_at <= cutoff` на всех дисках. Под lock повторно проверяются состояние и
дата удаления; восстановленные/исчезнувшие и вновь удалённые после cutoff файлы
пропускаются. Переход выполняет `StoredFile.request_purge`; состояние, отдельные
`files.purge` и continuation сохраняются атомарно. Продолжение имеет детерминированный
UUID и тот же cutoff, проверяется текущая worker lease перед commit. Уже
`purging` сохраняют свою job; их retry/recovery выполняет существующий механизм.
Физическое удаление всех версий выполняет штатный purge worker. Новых таблиц и
миграций нет; для развёртывания нужно обновить backend/Console и перезапустить
`dnk-manage jobs worker`, чтобы он зарегистрировал новый job type.

### Предпросмотр для администратора

`GET /api/console/files/items/{file_id}/preview/` возвращает содержимое готового
зарегистрированного файла на готовом диске текущего tenant. Требуются роль `admin`
и разрешение `files.read` для конкретного `stored_file` с `resource_id=file_id`.
Ownership бакета и объекта проверяется перед открытием потока. Другой tenant,
корзина, незавершённая загрузка и отсутствующий объект получают `404`.

Ответ потоковый: `Content-Disposition: inline` с UTF-8 именем, размер из реестра,
`private, no-store`, `nosniff`, CSP sandbox, same-origin framing. Форматы:
PDF, PNG/JPEG/GIF/WebP/AVIF/BMP, аудио MPEG/MP4/OGG/WebM/WAV, видео MP4/WebM/OGG;
поддержка codec зависит от браузера. Plain text/CSV/Markdown/JSON выдаются как
`text/plain; charset=utf-8`; bytes не перекодируются. HTML/SVG/XML, Office,
архивы и остальные форматы получают `415`, ownership conflict — `409`,
недоступность storage/configuration — `503`. Пути ОС и MinIO URL не принимаются.

Поток закрывается при EOF, ошибке, отмене, disconnect и ошибке commit UoW до
отправки ответа. SDK thread завершается до освобождения semaphore и tenant
admission. Endpoint описан в OpenAPI как binary response без Request body.
Range/HEAD и конвертация документов не реализованы.

В списке активных файлов `/admin/files` действие «Предпросмотр» доступно в
таблице и мобильных карточках. `FilePreviewDialog` показывает изображение,
встроенный PDF viewer, обычный текст или audio/video controls по MIME ответа.
Запрос выполняется через существующий authenticated HTTP client с cookies;
содержимое не помещается в общий query cache. Есть loading, сообщения об ошибках
403/404/409/415/503 и повтор запроса. Повреждённое изображение или неподдержанный
media codec также получает сообщение об ошибке.

Перед показом загружается весь файл как Blob; для большого файла нужно дождаться
окончания загрузки. Текст отображается через Vue interpolation без выполнения
разметки; после первых 256 КиБ показывается отметка об ограничении предпросмотра.
Окно закрывается по Escape/кнопке с возвратом фокуса к действию списка. Закрытие,
смена файла/tenant, смена вкладки и unmount отменяют запрос и освобождают Blob URL;
устаревший ответ не меняет новый предпросмотр. В корзине предпросмотра нет.

### Интерфейс файлового менеджера

Страница использует существующий shadcn-vue admin layout и компоненты:
четыре карточки категорий активных файлов, сводку активных/корзины/purging,
таблицы на desktop и карточки строк на mobile. Публичной квоты или фиктивного
свободного места нет. «Все диски» объединяет готовые диски; можно выбрать
несколько дисков и тип файла. Поиск с задержкой 300 ms и пагинация выполняются
на сервере; `search`, повторяемый `bucket_id`, `category`, `page`, `page_size`
сохраняются в URL. Размеры страницы: 10/20/50/100. После удаления последней
строки последней страницы интерфейс возвращается на оставшуюся страницу.

«Загрузить файлы» открывает форму с выбором готового диска и очередью файлов.
По умолчанию выбирается готовый системный диск, а при фильтре одного готового
диска — этот диск. Множественный выбор, drag-and-drop и вставка файлов из буфера добавляют файлы
в очередь; отдельные элементы можно убрать перед отправкой. Лимит каждого
файла — 1 ГиБ (1073741824 bytes), размер пакета не ограничивается суммой одного
запроса: каждый файл отправляется отдельным `POST /items/` последовательно.
У каждого файла собственные прогресс, результат и транзакция. Одинаковые имена
не перезаписываются. Процент передачи не означает успешное сохранение: форма
ждёт `201`. «Остановить после текущего» завершает текущий запрос и оставляет
остальные файлы в очереди. Результаты остаются видны до закрытия окна.

Подтверждённые успешные файлы повторно не отправляются; обычная ошибка сохраняет
файл для ручного повтора. При сетевом сбое, timeout или `5xx` результат может быть
неизвестен: пакет останавливается, список обновляется, автоматического повтора
нет. Для повтора этого файла нужно подтвердить проверку списка: повторный upload
создаёт отдельный файл. Остальные файлы можно продолжить независимо. `401/403/429`
также останавливают пакет. Ошибка обновления списка не меняет результат успешной
загрузки; смена tenant и unmount отменяют запрос и очищают очередь.

«В корзину» требует подтверждения, объясняя недоступность файла для связанных
модулей и восстановление в течение 30 дней. Корзина показывает даты удаления
и предельный срок, «Восстановить» и подтверждаемое «Удалить навсегда».
Для `purging` — «Удаляется», без восстановления; истёкший срок также блокирует
восстановление. Принятый запрос purge (`202`) означает начало фонового
удаления, а не уже освобождённый объём. При наличии `purging` на текущей
странице корзина обновляется раз в 5 секунд, только пока вкладка видима;
после завершения polling прекращается.

После мутаций обновляются списки, сводка и диски текущего tenant. Query keys
разделяют tenant/фильтры, устаревшие GET отменяются; смена tenant отменяет
мутации и закрывает формы. Loading/error/retry/empty состояния, обе темы,
клавиатура и мобильные действия проверены в Chromium на контрактных fixtures.
Console typecheck/lint/build прошли; 15 групп браузерных проверок успешны,
ошибок приложения и Vue warnings нет. Реальные cookies/MinIO/worker и сетевой
upload progress остаются предметом rollout smoke test; событие 100% в UI
проверялось синтетически с задержкой ответа. Backend этим UI-срезом не менялся.

Оба списка принимают `search` (trim, максимум 255 символов), повторяемый
`bucket_id` (максимум 50 UUID), `category` (`documents|images|videos|other`),
`page` (от 1) и `page_size` (`10|20|50|100`, default 20). Поиск по имени
регистронезависим и буквальный, включая `%`, `_` и `\\`; фильтры соединяются AND.
SQL возвращает страницу и total одним statement. Сортировка: активные файлы
по `created_at DESC, id DESC`, корзина по `deleted_at DESC, id DESC`.
Пустая или вышедшая за пределы страница сохраняет правильный total.

Без фильтра выбираются все готовые диски текущего tenant. Явно выбранный
неподготовленный диск даёт `409`, неизвестный или чужой — одинаковый `404`.
Неверные параметры дают `422`, отсутствие сессии — `401`, отсутствие роли
admin или дополнительного разрешения — `403`. Tenant/actor не принимаются
из query. Для overview действует только `bucket_id`; поиск/категория не
меняют сводку. MIME нормализуется без регистра/пробелов/параметров, документный
набор зафиксирован в `application/stored_file/file_category.py`; audio и
архивы относятся к `other`. Все четыре категории возвращаются даже при нулях.

Новые use cases имеют собственные Query/Handler/DTO, HTTP Response/controller
и именованный Depends. SQL read repository/mapper используют сессию внешнего
UoW; не загружают агрегаты и не выполняют внутренние commit или storage I/O.

HTTP-мутации:

- `POST /api/console/files/items/` → `201 UploadFileResponse`
  (`file_id, name, content_type, size_bytes`); multipart `file`, optional `bucket_id`.
- `DELETE /api/console/files/items/{file_id}/` → `200 TrashFileResponse`
  (`file_id, deleted_at, purge_after`); объект остаётся под прежним ключом.
- `POST /api/console/files/items/{file_id}/restore/` → `200 RestoreFileResponse`
  (`file_id, status=ready`); проверяются срок, готовность диска и owned-объект.
- `DELETE /api/console/files/trash/{file_id}/` → `202` без тела;
  переход в `purging` и отдельная `files.purge` job атомарны в SQL.

Мутации требуют trusted tenant admin, реальный session/flow-bound CSRF
(`Origin`, `X-CSRF-Token`, cookie) и соответствующее действие
`files.upload|trash|restore|purge`. Resource ID — file UUID, для upload — None.
Имя и MIME проверяются Domain; tenant/actor/key/dates не принимаются от клиента.
Request/Response каждого HTTP-метода отделены от Command/DTO; методы без тела
не имеют фиктивных схем. Все переходы существующего файла используют lock;
часы читаются после его получения. Повтор trash/purge сохраняет даты/job.
На границе срока и после запроса purge восстановление возвращает `409`.

Console multipart ограничивается до записи очередной части в spool, включая
приём без Content-Length. Фактический `UploadFile.size` передаётся существующему
upload handler; MIME по умолчанию `application/octet-stream`. Spool переходит
на диск после 1 МиБ и закрывается при успехе, ошибке, обрыве и отмене.
Полное тело ограничено file limit + 64 КиБ; заголовки каждой части — 64 КиБ,
текстовое поле — 1 КиБ, принимаются один файл и максимум один bucket ID.
Лимит превышен — `413`, повреждённый multipart/лишние поля — `422`.
Приём ограничен `FILES__OPERATION_TIMEOUT_SECONDS` (`408` по истечении);
передача в MinIO сохраняет собственный bounded timeout/concurrency.
Helm: `application.files.consoleMaxUploadBytes`; Compose и template env
передают тот же setting. Nginx Console и control-plane tenant proxy для
`/api/console/files/items/` пропускают 1073807360 bytes (1 ГиБ + 64 КиБ),
отключают request buffering и используют HTTP/1.1, timeout 600 s.
Для nginx ingress Helm вычисляет body limit как consoleMaxUploadBytes + 65536
и proxy read/send timeout из operationTimeoutSeconds (с округлением вверх).
Явные ingress.annotations сохраняются. Для другого ingress controller оператор
должен настроить лимит и timeout самостоятельно. При изменении backend setting
в Compose согласуйте также статический лимит Nginx. После обновления нужны
пересборка Console и перезапуск backend/proxy; старое явное значение env/Helm
имеет приоритет над новым default.

`202` подтверждает durable запрос; штатный `jobs worker` обрабатывает `files.purge`
и удаляет реестр после физического подтверждения. Для корзины используется
`files.trash.cleanup`, без MinIO TTL. Браузерные формы/AdminLayout относятся к срезу UI.

## Контракт потребителя

В своём Application слой потребитель объявляет порт загрузки/чтения и собственный
DTO. Infrastructure adapter вызывает `UploadFileHandler`/`GetFileContentHandler`
через внешнюю сборку `build_files_handlers(session, resolver)`.
Сессия передаётся из того же tenant UoW, в котором сохраняется бизнес-ссылка.
Схема должна быть привязана к trusted tenant, а TenantGate удерживаться до
завершения операции; module handler не открывает и не фиксирует UoW.
При ошибке загрузки потребитель откатывает UoW целиком.

Upload принимает BinaryIO, точный размер, filename, MIME и optional bucket ID;
возвращает file UUID и метаданные. Источник должен поддерживать ограниченное
чтение `read(n)`. Проверяются слишком короткие и слишком длинные источники,
включая нулевую длину; SDK передаёт крупные файлы multipart без чтения целиком.

Get возвращает управляемый async stream с порциями до 64 KiB и метаданными.
Поток независим от DB-сессии, но caller сохраняет admission до окончания чтения.
Используйте `try/finally: await result.stream.aclose()` и при раннем прекращении
отдачи. Отсутствующий ID и ID другого tenant дают `FileNotFoundError`.
Конкретный бизнес-модуль выбирает download endpoint, ACL, Content-Disposition,
Content-Type и cache policy. Files не знает о товарах, контактах или документах.

## Корзина: worker и восстановление заданий

Перед удалением проверяется использование файла. `FileUsagePort` получает факты
через публичные запросы Catalog и Channels, собранные на той же tenant-сессии.
Files не читает чужие SQL-модели. Ссылки Catalog, все сохранённые overrides
(включая неактивные локали и выключенный экспорт) и выполняемые media-передачи
защищают файл. Исторический кеш внешнего media ID без живых ссылок файл не удерживает.

Проверка выполняется после write lock файла и до изменения состояния. Trash и
явный purge возвращают `409 {detail: {code: "file_in_use"}}`; Console объясняет,
что файл нужно убрать из галерей или дождаться завершения передачи. Массовая и периодическая
очистка пропускают используемые записи, сохраняя продвижение курсора. Физический
purge worker тоже проверяет использование до SDK-вызова — это защищает ранее
поставленные задания и старые purging-записи. Usage-запросы не берут locks потребителей,
чтобы не нарушать порядок Catalog/Channels → Files. Добавление ссылки должно
проверять ready под тем же Files lock; конкурентное удаление не оставляет битых ссылок.

Проверки: `test.test_files_usage` и media/PostgreSQL-сценарии Channels.

`files.trash.cleanup` регистрируется при запуске `jobs worker` и каждый час для
подготовленных существующих tenant без повторного onboarding. Registrars модулей
независимы при сбое. Проверяется штатный admission: `freeze` разрешён текущей
политикой TenantGate; deleting/blocked и exclusive gate откладывают обслуживание.

Порция содержит не более 100 candidate IDs и проверяется заново под write lock.
Domain допускает автоматическое удаление после ровно 720 часов в UTC. Состояние
`purging` и `files.purge` сохраняются одной транзакцией. Keyset continuation
записывается вместе с порцией, сохраняет cutoff/cursor и имеет UUID5 ID от parent
job/cursor. Повтор и restart не теряют следующие страницы и не дублируют jobs.

Для `purging` с missing/terminal (`failed`, `canceled`, `done`) job создаётся новый
ID без изменения дат. `scheduled`/`running` не дублируются; expired leases сначала
восстанавливает shared worker. Задания с исчерпанными попытками восстанавливаются
ближайшим часовым проходом. Новое окно начинает сканирование с начала реестра.

Purge worker использует собственные admission/tenant UoW, lock файла и проверки
worker lease до выполнения/перед commit. Старые file job IDs и исчезнувшие записи —
no-op. MinIO port удаляет все owned-версии и delete markers точного ключа, проверяет
bucket tags и metadata каждой версии и подтверждает отсутствие повторным listing.
Бакет и соседние ключи остаются. SQL-запись удаляется только после подтверждения.
Отмена ждёт SDK перед освобождением gate/row lock.

При outage запись остаётся `purging`; shared jobs планируют retry. При сбое SQL
после physical delete повтор допускает отсутствие объекта или owned-бакета.
Потеря lease откатывает SQL, новая доставка повторяет подтверждение.
Очистка не гарантирует удаление в точную секунду: при исправном worker запрос
появится на ближайшей часовой проверке, задержка удаления зависит от очереди/MinIO.

Метрики worker: `files_trash_backlog_files`/`files_trash_backlog_bytes`
(`tenant_id`, `state=expired|pending`), `files_trash_max_purge_delay_seconds`
(старейший overdue срок, включая ожидающие purge),
`files_trash_queued_total` (`kind=new|recovery`), `files_purge_deliveries_total`
(`outcome=committed|stale|deferred|retryable_failure|exhausted`) и
`files_purge_duration_seconds`. Backlog обновляется после commit и отражает
последний scan данного процесса; между проходами это не live quota, а samples
удалённых tenant исчезают после перезапуска процесса. Итоги не содержат имён,
payload/config/SDK responses. Состояния повторов видны также в shared jobs.

Исправлена регистрация обеих hourly Files jobs: проверка таблицы завершает свою
lookup-транзакцию до UoW, поэтому INSERT не откатывается при освобождении admission.

## Обслуживание

Jobs worker регистрирует `files.cleanup` каждый час; первая job создаётся
в SQL-транзакции onboarding. Cleanup касается только ready-бакетов и объектов
старше 24 часов, owned по имени/tags/metadata, без записи в файловом реестре.
Также abort выполняется для старых multipart uploads с module UUID key.
Защитный интервал больше максимального времени upload.

Для установленного MinIO используется собственное обслуживание multipart:
его S3 lifecycle action `AbortIncompleteMultipartUpload` не поддерживается
этой версией сервера. См. [S3 compatibility MinIO](https://minio.community/community/minio-object-store/reference/s3-api-compatibility.html).
Python SDK 7.2.20 предоставляет list/abort multipart только private methods;
они изолированы в адаптере, версия закреплена `uv.lock`, совместимость покрывают
реальные интеграционные проверки. При обновлении SDK повторить эти проверки.

Purge Tenant очищает физическое хранилище прежде schema drop. Сбой MinIO
оставляет Tenant заблокированным для повторной попытки и сохраняет реестр.
Storage adapters работают вне event loop; отмена ожидает завершения текущего
SDK вызова, чтобы его внешние эффекты не продолжались после release admission.

## Проверки

`test/test_files.py` — инварианты, размеры, расширяемый resolver, потоки/отмена.
`test/test_files_lifecycle.py` — 30-дневная граница, DST/UTC, фабрики, повторы,
замена job и устаревшие подтверждения.
`test/test_files_lifecycle_postgres.py` — миграция с данными, guarded downgrade,
ограничения, rollback, условное удаление, locks и конкурентные restore/purge.
`test/test_files_workers_postgres.py` — purge/версии/ownership, 30-дневная граница,
111 кандидатов/continuation, crashes/outages/lease/cancellation, обе регистрации,
штатный recovery/exhausted и повтор без объекта/бакета.
`test/test_files_architecture.py` — полнота 16 сценариев, DTO, зависимости,
аннотации/docstrings, фабрики и границы транзакций.
`test/test_files_postgres.py` — настоящие PostgreSQL/MinIO: пустые и multipart
файлы, tenant isolation, private access, rollback/orphan cleanup, provisioning
retry, ownership, purge и безопасный read-only HTTP.
Тестовые сервисы `scripts/cicd/check_environment.py` создаются изолированно
и удаляются после запуска. Проверки Control Plane, tenant deletion, Identity
и миграций покрывают интеграцию с жизненным циклом Tenant.

Проверки этой реализации: 80 сценариев Files/Tenancy/Control Plane/Identity/
миграций успешно выполнены; пропущенная Redis namespace проверка отдельно
успешно выполнена на disposable Redis. Архитектура и module registration
проверены отдельно; 98 offline Helm tests прошли. Console прошёл `vue-tsc -b`,
ESLint, Vite build и Chromium QA с API fixtures на ширинах 1440 и 390 px:
статистика, read-only controls, refresh, error, empty state, отсутствие overflow.
Полный backend suite первоначально выполнил 674 теста и выявил ошибку только
в новом cancellation mock; она исправлена и сценарий повторно прошёл.
Production rollout и браузерное подключение к реальному Instance в этот запуск
не выполнялись. Google Drive и endpoints потребителей остаются следующими этапами.

Срез Domain/persistence корзины проверен отдельно: 81 уникальный тест Files,
миграций, архитектуры, регистрации модулей, scheduled jobs и удаления tenant
прошёл после обновления ожидаемого tenant head. Изолированные сервисы удалены.
Новые Console API/UI, purge worker и production rollout в этот срез не входят.

Срез Read API проверен отдельно: 28 прикладных/HTTP/PostgreSQL/Domain/
архитектурных тестов прошли на текущем Files с изолированной регистрацией
моделей. Регрессия из 96 тестов с настоящими PostgreSQL/MinIO/Redis/RabbitMQ
прошла на текущем Files поверх последнего коммита остальных модулей.
Black, compile и аудит архитектуры/diff выполнены. Общий прогон текущего
workspace остановился на отсутствующем `Catalog product_type_block` в
параллельно изменяемой tenant metadata; совместная проверка окончательной
версии этих изменений остаётся ограничением. Мутации, Admin UI и purge worker
в Read API срез не входят; рабочие tenant-схемы не изменялись.

Срез HTTP-мутаций: 109 регрессионных тестов Files/PostgreSQL/MinIO/миграций/
архитектуры/регистрации/jobs/удаления tenant прошли на текущем Files поверх
последнего коммита остальных модулей; 98 Helm tests успешны. Проверены реальные
CSRF/action permissions, атомарность file/job, concurrent purge requests,
двойная проверка срока restore вокруг storage I/O, rollback после job INSERT
и на commit, пустые/одинаково названные файлы, streaming limit, timeout,
закрытие spool, ошибки storage/ownership и OpenAPI. Black, compile и полный
архитектурный аудит выполнены. Совместный прогон workspace остановился на
параллельно изменяемой Catalog-миграции (`is_variation`: boolean с integer default);
сами файловые операции в успешном прогоне проверены на одноразовых сервисах.
На момент среза 3 worker и Admin UI ещё не были поставлены; рабочие данные не изменялись.


Срез worker/recovery: 121 регрессионный тест прошёл с текущим Files поверх
последнего коммита остальных модулей. Последний совместный workspace-прогон:
107/108 успешны, включая Files/worker/jobs; отдельная ошибка Catalog/Currency
migration downgrade затрагивает ожидаемые `currency_exchange_rate_books/quotes`.
Предыдущий совместный прогон также выявил 13 ошибок tenant deletion (включая
subtests): administrator role, отсутствующая cloud_identities и HTTP admission.
Чужие изменения не исправлялись/не откатывались; полный workspace suite пока
не зелёный. Финальные target-проверки: 8 ownership/bucket/registrar/архитектура,
6 boundary/recovery/backlog/архитектура и 18 offline проверок успешны.
Black (178 файлов), compile, scoped diff check и полный архитектурный аудит
16 сценариев выполнены. Все сервисы одноразовые и удалены; рабочие данные и
rollout не затрагивались. Следующий срез — Admin Console UI.
