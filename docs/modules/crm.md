# CRM

CRM — контекст с самостоятельными агрегатами контактов и компаний. На текущем
этапе реализованы самостоятельные агрегаты `ContactEntity` и `CompanyEntity` с
созданием, чтением, обновлением и удалением. Связь между ними управляется через
существующую SQL-модель `contact_companies` без отдельного Aggregate Root.

## Создание контакта

Аутентифицированный участник tenant может выполнить `POST /api/console/crm/contacts`.
Запрос требует обычной session authentication и CSRF-защиты Console: корректных
`Origin`, `X-CSRF-Token` и привязанных к токену cookies. Роль администратора не требуется.

```json
{
  "first_name": "  Анна-Марія ",
  "last_name": " O'Neill ",
  "middle_name": null
}
```

Обязательно только `first_name`: после удаления пробелов по краям оно должно
содержать 1–255 символов. `last_name` и `middle_name` необязательны: отсутствие,
`null`, пустая строка и строка из пробелов означают `null`. Каждое непустое
значение также ограничено 255 символами.
Внутренние пробелы, регистр, дефисы и апострофы сохраняются. Одинаковые ФИО разрешены.

Неизвестные поля запрещены. Клиент не передаёт ID, tenant, actor, аудит, телефоны,
email или связи с компаниями. UUIDv7 генерируется сервером; tenant и автор берутся
из доверенного `RequestContext`.

### Ответ

После успешного commit возвращается `201 Created`:

```json
{
  "id": "019f0db0-0000-7000-8000-000000000001",
  "first_name": "Анна-Марія",
  "last_name": "O'Neill",
  "middle_name": null,
  "created_at": "2026-09-28T12:00:00Z",
  "updated_at": "2026-09-28T12:00:00Z",
  "created_by": "11111111-1111-4111-8111-111111111111",
  "updated_by": "11111111-1111-4111-8111-111111111111"
}
```

При создании обе даты равны одному показанию UTC clock, оба автора — текущему
пользователю. Ответ не содержит заглушек для связанных сущностей.

### Ошибки

- `401`: отсутствует аутентификация.
- `403`: отсутствует tenant или нарушена CSRF-защита.
- `422`: неверный тип, неполное/слишком длинное имя или лишние поля.
- `409`: конфликт первичного ключа контакта.
- `500`: неожиданный сбой хранения или commit; успешный ответ не отправляется.

## Получение контакта по ID

`GET /api/console/crm/contacts/{contact_id}` возвращает сохранённые данные одной
записи текущего tenant. ID в URL должен быть UUID. Доступен аутентифицированному
участнику tenant; роль admin, CSRF-токен и заголовок Origin для GET не требуются.
Tenant определяется только доверенным `RequestContext`, а не параметрами запроса.

### Ответ

`200 OK` содержит `id`, `first_name`, `last_name`, `middle_name`, `created_at`,
`updated_at`, `created_by`, `updated_by`. UUID передаются строками, даты — в формате
ISO 8601. Телефоны, email и компании в ответ не входят.

Фамилия и отчество могут быть `null`. Сохранённые имена не нормализуются
повторно; GET не изменяет данные и аудит.

### Ошибки

- `401`: отсутствует аутентификация.
- `403`: отсутствует tenant в доверенном контексте.
- `422`: некорректный UUID в URL.
- `404`: контакт отсутствует в текущем tenant. Запись другого tenant даёт тот же
  ответ `{"detail": "Contact not found."}`, не раскрывая её существование.
- `500`: неожиданный сбой чтения или завершения транзакции; успешный ответ не отправляется.

## Список контактов

`GET /api/console/crm/contacts` возвращает `200 OK` и массив всех контактов
текущего tenant. Фильтрации, поиска и пагинации нет; порядок — `created_at`, затем
`id`. Элементы имеют формат GET по ID.
Пустой список — `[]`. Требуются аутентификация и tenant-контекст, CSRF не нужен.

## Обновление контакта

`PUT /api/console/crm/contacts/{contact_id}` полностью заменяет ФИО. В теле
обязательно только строковое `first_name`; пропущенные `last_name` и
`middle_name` становятся `null`.

`PATCH` по тому же URL меняет только переданные части. Пустое тело `{}` запрещено;
явные `last_name: null` и `middle_name: null` очищают соответствующие поля.
`first_name` можно не передавать, тогда сохраняется текущее имя; явное `null`
или пустое имя отклоняется. Оба метода применяют правила нормализации POST и возвращают `200 OK`
с полным ФИО и аудитом. При изменении обновляются `updated_at` и `updated_by`;
повторная передача того же нормализованного ФИО сохраняет прежний аудит.
При загрузке на изменение ФИО восстанавливается как `ContactNameVO` и
проверяется по доменным правилам.

Оба метода требуют аутентификации, tenant-контекста и CSRF. Неизвестные поля,
включая ID и аудит, дают `422`. Отсутствующий контакт даёт `404` с
`Contact not found.`; запись другого tenant также не раскрывается.

## Удаление контакта

`DELETE /api/console/crm/contacts/{contact_id}` физически удаляет запись.
Успех — `204 No Content` без тела, отсутствие — `404`. Требования к
аутентификации, tenant и CSRF те же, что у PUT/PATCH. Существующий внешний ключ
`ON DELETE CASCADE` удаляет связи контакта с компаниями.
Связи с ContactPoints очищаются тем же UoW перед удалением контакта.

## Компания

Аутентифицированный участник tenant может читать и изменять компании без роли
администратора. Запись требует CSRF; tenant и actor берутся из доверенного
`RequestContext`. ID генерируется сервером через общий UUID-порт.

| Метод | URL | Результат |
| --- | --- | --- |
| `POST` | `/api/console/crm/companies` | `201 Created`, полная запись |
| `GET` | `/api/console/crm/companies/{company_id}` | `200 OK`, одна запись |
| `GET` | `/api/console/crm/companies` | `200 OK`, массив всех компаний tenant |
| `PUT` | `/api/console/crm/companies/{company_id}` | `200 OK`, полная замена бизнес-полей |
| `PATCH` | `/api/console/crm/companies/{company_id}` | `200 OK`, изменение переданных полей |
| `DELETE` | `/api/console/crm/companies/{company_id}` | `204 No Content` без тела |

Единственное бизнес-поле текущей SQL-модели — `legal_name`. POST и PUT требуют
строку `legal_name`; PATCH допускает её отсутствие в схеме запроса, но пустой
объект `{}` и явный `null` отклоняются, поскольку других изменяемых полей пока
нет. Пробелы по краям удаляются; результат должен содержать 1–255 символов.
Внутренние пробелы, регистр и знаки сохраняются. Одинаковые названия разрешены.
Неизвестные поля, включая ID, аудит и связи с контактами, дают `422`.

POST, GET, LIST, PUT и PATCH возвращают `id`, `legal_name`, `created_at`,
`updated_at`, `created_by`, `updated_by` (список — массив таких объектов).
Список не поддерживает фильтрацию, поиск и пагинацию и отсортирован по
`created_at`, затем `id`. Повторное PUT/PATCH с тем же нормализованным названием
сохраняет прежний аудит. GET и LIST не изменяют сохранённое название.

Без аутентификации ответ `401`; без tenant либо при нарушении CSRF — `403`.
Некорректный UUID, тело или название дают `422`; отсутствующая в текущем tenant
компания — `404` с `Company not found.`. Конфликт первичного ключа при создании
даёт `409`; неожиданный сбой хранения или commit — `500`, без успешного ответа.
DELETE физически удаляет компанию; существующий FK с `ON DELETE CASCADE`
удаляет строки `contact_companies`.
Связи с ContactPoints удаляются в той же транзакции, что и компания.

## Контактные данные Contact и Company

ContactPoints — отдельный модуль-расширение: он владеет нормализацией телефонов
и email, справочником значений, подписями и привязками. CRM проверяет существование
владельца и блокирует его запись перед изменением привязок. Значения не входят в
агрегаты `ContactEntity` и `CompanyEntity`, их основные GET/POST/PUT/PATCH схемы
не изменены.

| Действие | Contact | Company |
| --- | --- | --- |
| Читать | `GET /api/console/crm/contacts/{contact_id}/contact-points` | `GET /api/console/crm/companies/{company_id}/contact-points` |
| Полностью заменить | `PUT` по тому же URL | `PUT` по тому же URL |
| Изменить переданные списки | `PATCH` по тому же URL | `PATCH` по тому же URL |

GET возвращает `200 OK` с `phones` и `emails`; у нового объекта это пустые
массивы. Каждый элемент содержит `binding_id`, `contact_point_id`, нормализованное
`value`, `country_code`, `label_id` и `position`. PUT требует оба массива и
полностью заменяет их. PATCH допускает отсутствие массива: такой список остаётся
без изменений; `[]` очищает его, явный `null` запрещён. Пример записи:

```json
{
  "phones": [{"value": "050 123 45 67", "country_code": "UA", "label_id": null}],
  "emails": [{"value": "Name@Example.COM", "binding_id": null}]
}
```

При редактировании существующего элемента клиент передаёт его `binding_id`.
`contact_point_id`, tenant, actor и аудит не принимаются. UUID новых точек и
привязок генерируются сервером. Оба метода записи возвращают `200 OK` с полными
нормализованными списками после commit. Требуются аутентификация и tenant;
для PUT/PATCH также CSRF. Отсутствующий владелец даёт `404`, ошибка схемы или
значения — `422` (для элемента с адресом поля), конфликт хранения — `409`.
Сбой транзакции не даёт успешного ответа.

CRM Application зависит от собственного `ContactPointsPort`. Его инфраструктурный
адаптер использует команды и запросы ContactPoints с ключами `crm.contact` и
`crm.company`. Оба модуля работают в общей сессии UoW; только внешняя граница
завершает транзакцию. При удалении CRM вызывает очистку привязок до удаления
владельца. Справочник значений ContactPoints при этом сохраняется: одно значение
может использоваться несколькими объектами.

## Связь контакта и компании

Одна строка `contact_companies(contact_id, company_id)` представляет связь в обоих
направлениях. Для существующей пары Contact и Company PUT создаёт связь, а
повторный PUT оставляет её без изменений. DELETE удаляет связь; повторный DELETE
также успешен. Оба метода возвращают `204 No Content` без тела.

| Действие | От контакта | От компании |
| --- | --- | --- |
| Связать | `PUT /api/console/crm/contacts/{contact_id}/companies/{company_id}` | `PUT /api/console/crm/companies/{company_id}/contacts/{contact_id}` |
| Отвязать | `DELETE` по тому же URL | `DELETE` по тому же URL |
| Список | `GET /api/console/crm/contacts/{contact_id}/companies` | `GET /api/console/crm/companies/{company_id}/contacts` |

Список от контакта возвращает полные проекции связанных компаний (`id`,
`legal_name`, аудит); список от компании — полные проекции контактов (`id`, ФИО,
аудит). Оба отсортированы по `created_at`, затем `id` связанной записи.
Существующий объект без связей возвращает `[]`, отсутствующий — `404`. Оба PUT и
DELETE возвращают `404`, если отсутствует хотя бы один из двух объектов в текущем
tenant; отсутствие самой строки связи при DELETE не считается ошибкой.

Чтение требует аутентификацию и tenant-контекст, запись дополнительно требует
CSRF. Неверный UUID даёт `422`, отсутствие аутентификации — `401`, отсутствие
tenant или нарушение CSRF — `403`. Обе стороны URL используют один сценарий записи
и одну tenant-сессию UoW. Список формируется одним LEFT JOIN без загрузки
агрегатов по одному. Связь не имеет колонок аудита, поэтому изменение связи не
меняет аудит Contact или Company. При удалении любого из них существующий FK
каскадно удаляет строку связи.

## Слои и транзакция

- `domain/contact/`: агрегат `ContactEntity`, `ContactIdVO`, неизменяемый
  `ContactNameVO`, доменные ошибки и контракт репозитория записи.
- `application/contact/command/create_contact/`: команда, handler и DTO результата.
  Handler получает генератор UUID через порт, создаёт агрегат, сохраняет его и
  возвращает ФИО с аудитом. Контроллер не формирует ID контакта.
- `application/contact/query/get_contact/`: `GetContactQuery`, `GetContactHandler`
  и `ContactDetailsDTO`. Порт `ContactQueryRepositoryProtocol` расположен в
  `application/contact/port/query_repository.py`.
- `application/contact/query/list_contacts/`: список через тот же порт проекций.
- `application/contact/command/update_contact/` и `delete_contact/`: изменение
  и удаление через заблокированный агрегат в общем UoW. PUT и PATCH вызывают
  один метод `ContactEntity.update()` после объединения переданных полей.
- `infrastructure/contact/persistence/`: раздельные репозитории записи и чтения.
  `ContactMapper` готовит INSERT/UPDATE values и восстанавливает агрегат для
  изменения; `ContactQueryMapper.to_details()` переносит проекцию чтения в DTO.
  Чтение по ID выполняет
  один SELECT явных колонок по ID, без блокировки и загрузки связей. Tenant admission
  один раз привязывает `schema_translate_map` к соединению запроса до создания UoW;
  оба репозитория используют общую сессию без выбора схемы в каждом SQL-выражении.
  Один HTTP UoW работает с одной tenant-схемой.
- `presentation/contact/router.py`: маршруты агрегата; в `http/request/` и
  `http/response/` каждая схема находится в файле своего метода, в
  `http/controller/` — отдельный файл для каждого контроллера. PUT и PATCH
  явно собирают свои команды и ответы. `depends.py` собирает зависимости. Общий `UoWDep`
  передаёт сессию репозиторию и завершает транзакцию до отправки ответа.
- `domain/company/`: `CompanyEntity`, `CompanyIdVO`, неизменяемый
  `CompanyLegalNameVO`, ошибки и контракт репозитория записи.
- `application/company/`: отдельные сценарии Create, Get, List, Update, Delete.
  PUT и PATCH вызывают один `UpdateCompanyHandler`, но имеют явные контроллеры и
  собственные HTTP-схемы.
- `infrastructure/company/persistence/`: репозитории чтения и записи, mapper
  агрегата и mapper проекции. Используют ту же сессию UoW с выбранной tenant-схемой.
- `presentation/company/`: router и depends агрегата, отдельные контроллеры
  шести HTTP-методов и отдельные файлы схем для каждого применимого метода.
- `domain/contact/value_object/company_link.py`: неизменяемая типизированная
  пара ID без отдельного Aggregate Root.
- `application/contact/command/link_company/` и `unlink_company/`: единые
  обработчики записи для обоих направлений URL. Порт связи находится в
  `application/contact/port/`.
- `application/contact/query/list_companies/` и
  `application/company/query/list_contacts/`: независимые проекции чтения.
- Репозиторий записи связи находится в `infrastructure/contact/persistence/`,
  проекции чтения — в инфраструктуре соответствующего агрегата. Общая сборка
  обработчиков записи находится в `presentation/depends/company_link.py`.

Domain и Application не зависят от SQLAlchemy/FastAPI. Handler и repository не
выполняют commit/rollback. Domain events и Outbox в этом сценарии не используются.
Импорты прямые, из файлов определений, без реэкспортов через `__init__.py`.

## Хранение и совместимость

Существующие модели остаются в `infrastructure/persistence/models/`, каждая в своём файле:

- `contact.py`: `ContactModel`, таблица `contacts`.
- `company.py`: `CompanyModel`, таблица `companies`.
- `contact_company.py`: `ContactCompanyModel`, таблица `contact_companies`.

Все три зарегистрированы в tenant metadata. SQL-модели, ограничения, индексы,
внешние ключи и миграции не изменены. Новая миграция не требуется.

Обязательное `first_name` — инвариант агрегата при создании и изменении.
Столбцы `last_name` и `middle_name` остаются nullable; SQL-модель и миграции
не требуют изменений.

Неподдерживаемый метод существующего маршрута возвращает `405`, отсутствующий
маршрут — `404`. Самостоятельный модуль `contact_points` продолжает работать,
но создание Contact пока с ним не интегрируется.

Существующие экраны Console не изменены. Их старый контракт содержит телефоны,
email и компании, поэтому форма пока несовместима с новым минимальным POST API.
Адаптация интерфейса будет отдельной задачей.

Исторический [runbook удаления CRM](../operations/remove-crm.md) к этой реализации
не применяется: он описывает удаление данных, а текущая схема сохраняется.

## Проверки

```sh
uv run python -m unittest test.test_crm_contact test.test_crm_contact_http test.test_crm_contact_get test.test_crm_contact_get_http test.test_crm_contact_mutations test.test_architecture_boundaries test.test_removed_module_boundaries
uv run python -m unittest test.test_crm_company test.test_crm_company_http
uv run python -m unittest test.test_crm_relations test.test_crm_relations_http
TEST_POSTGRES_URL=postgresql+asyncpg://... uv run python -m unittest test.test_crm_contact_postgres test.test_crm_company_postgres test.test_crm_relations_postgres test.test_tenant_migrations_postgres
```

PostgreSQL-проверки запускаются только на одноразовой тестовой базе. Они проверяют
аудит, нормализацию, создание, чтение, изменение, удаление, изоляцию tenant,
rollback и каскадное удаление связей Company; для Contact также проверяется
проекция чтения с nullable-столбцом. Отдельно
проверяется отсутствие изменений схемы при Alembic autogenerate.
