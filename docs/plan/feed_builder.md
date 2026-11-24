# **FeedBuilder — финальный целевой план реализации**

**Архитектура:** DDD + Clean Architecture\
**Backend:** Python, FastAPI, SQLAlchemy Async, PostgreSQL\
**Frontend:** Vue 3, TypeScript, TanStack Vue Query\
**Определения:** сохранённая JSONB-схема Feed с типизированными условиями и AST\
**Целевой MVP:** один выбранный Generic CSV либо XML на Feed, плоская выгрузка простых товаров и выбранных вариантов, расчёт денежных полей внутри Feed

Документ фиксирует согласованную целевую модель и последовательность реализации.
Все поля пользовательские и равноправные; обычный Feed начинается с пустой схемы.
Наценки/условия/формулы находятся в определении конкретного денежного поля.
Денежные значения FeedBuilder — точные числовые суммы. Необязательный код валюты
принадлежит полю и служит меткой результата; он не выполняет конвертацию.
Курс пользователь задаёт обычной константой своей формулы. Курсовых сервисов,
автоматического наследования валюты источника и FX-контекста модуль не использует.
Реализованы Feed CRUD, конструктор сохранённой схемы, управление ассортиментом,
предпросмотр денежного поля, расчёт и ручные значения полей публикации,
пробный CSV.
В срезе 16.7 `FeedExportState` заменяет объектную модель `FeedGeneration`.
CSV и XML собираются через `scheduled_jobs` и доступны по публичной ссылке
на хосте tenant. Активный файл хранится в Files и виден в Storage. Для обоих
форматов доступны `STRICT` и `SKIP_INVALID`. Приватная выдача остаётся отдельным шагом.

## **1. Цель, границы и порядок реализации**

FeedBuilder — самостоятельный bounded context, создающий пользовательские
выгрузки из Catalog. Catalog — единственный источник товарных данных фида.
Схема, условия, формулы и ручные значения публикаций определяют представление
этих данных в выгрузке. Условия и формулы цены принадлежат денежному полю
конкретной схемы Feed.

В MVP сохранённые в Feed схема и `export_settings` — актуальная конфигурация
для предпросмотра, пробного CSV и следующего обновления. `FeedExportState` хранит
снимок конфигурации на время незавершённой задачи, отчёт последней завершённой
проверки и ссылку на один активный файл Files. Публичный URL живёт на хосте
tenant. История схем и публикация выбранной ревизии относятся к расширениям
после MVP (раздел 17).

### **1.1. Целевые возможности MVP**

1. Создать Feed с названием, кодом, явно выбранным CSV либо XML и пустой пользовательской схемой.
2. Собрать структуру предложения из полей STRING, TEXT, MONEY, INTEGER и BOOLEAN.
3. Выбрать каждому полю источник или ручное заполнение, язык/валюту,
   ограничения, преобразования и экспортное имя.
4. Для MONEY выбрать прямой источник либо условный расчёт с формулой по умолчанию.
5. Задать IF/ELSE IF правила по категориям и другим зарегистрированным параметрам
   товара, используя обычную, акционную и закупочную цены из Catalog.
6. Привязать простые товары и выбранные варианты Catalog, просматривать значения/ошибки
   и задавать независимые overrides каждой позиции.
7. Сохранять схему в Feed, проверять её на предпросмотре и скачивать пробный CSV.
8. Асинхронно генерировать через `scheduled_jobs` один Generic CSV либо XML из
   проверенного набора записей по снимку сохранённой схемы и настроек Feed.
9. Получать текущий файл по HTTPS-ссылке на хосте tenant. Ошибка последней
   проверки отображается в отчёте, а ссылка продолжает выдавать активный файл.

| Тип поля | Значение | Контекст |
| --- | --- | --- |
| STRING | str | Локализованный или языконезависимый текст |
| TEXT | str | Описание и длинный текст |
| MONEY | PriceAmountVO с Decimal и PriceValueVO для результата | Необязательная валютная метка поля, источник или формула |

Локаль и необязательная валютная метка задаются полям, не всему Feed. Денежная формула
может выбирать источник, применять процентную/фиксированную надбавку и рассчитывать
маржу арифметическим выражением; отдельные типы политик для этого не требуются.

Единственный Product Mode MVP — VARIABLE_TO_SINGLE, он же режим по умолчанию
в Feed.export_settings.product_mode. Простой товар и каждый выбранный вариант
выгружаются самостоятельными предложениями по общей схеме. Контейнер VARIABLE
не создаёт отдельную экспортную запись; режим не подключает весь Catalog автоматически.

Условия по категориям входят в MVP как чтение параметров товара. Управление
категориями и выгрузка их дерева, группировка вариантов и представление семейств,
изображения, отдельные специализированные типы характеристик, AI-генерация,
динамический ассортимент, расписания, пресеты и форматы площадок Prom/Rozetka —
последующие расширения.
Параметры для условий доступны только через зарегистрированные публичные контракты.

### **1.2. Равноправные поля и пустая схема**

Все поля равноправны. У них нет системной роли или особого положения по имени.
Title, description, price и currency в примерах — пользовательские ключи,
не обязательные встроенные поля. При обычном создании Feed они не добавляются.
Пользователь сам определяет состав предложения, имена, required и экспорт.

- Пустая схема корректна при создании и сохранении Feed.
- constraints.required требует значения в публикации, а не наличия поля
  с определённым именем во всех Feed.
- field_id — стабильная идентичность поля; переименование key/label/export.name
  и перестановка не создают новое поле.
- Состав произволен в пределах поддерживаемых типов и структурных ограничений.
- Для генерации Generic CSV/XML требуется хотя бы одно экспортируемое поле.
  Состав и ключи полей определяет пользователь.
- При несовместимой смене типа или локали существующего поля создаётся новый
  field_id. Необязательную валютную метку, формулы и ограничения можно менять
  с сохранением ID совместимого поля. Проверка эволюции по истории ревизий
  относится к расширению после MVP.

### **1.3. Первый срез: только объекты Domain Feed**

Непосредственный первый срез ограничен Aggregate Root Feed, зависимыми Entity,
VO, enums, чистыми структурными Policy, ошибками создания и unit-тестами.
У Feed, FieldDefinition и ConditionalPriceRule реализуются только create()
и restore(); VO проверяют
собственные значения. Каждый VO хранится в своём файле.

На этом шаге нет методов редактирования/публикации/генерации, вычислителя формул,
событий, репозитория, Application, SQL, API или UI. Ниже описан полный целевой
модуль для последующих срезов; его будущие контракты не являются поручением
создать их заготовки в первом срезе. Структурные Policy проверяют определения
при конструировании, но не исполняют условия, формулы или жизненный цикл Feed.

#### **1.3.1. Предыдущий объектный срез Publication, Generation и AccessKey**

После объектов Feed добавлены `FeedPublication`, `FeedGeneration` и
`FeedAccessKey` с фабриками create/restore и проверками состояния. У генерации
в этом срезе была доменная Entity `FeedArtifact`.

В целевой модели `FeedExportState` заменяет `FeedGeneration` и `FeedArtifact`.
`FeedPublication` уже имеет сохранённое участие и overrides. Объект
`FeedAccessKey` остаётся за пределами ближайшей публичной вертикали.
Файлы хранятся через Files по разделам 3.8 и 5.6.

#### **1.3.2. Реализованный первый рабочий срез: Feed CRUD**

Один Feed создаётся как DRAFT с пустой схемой и обязательным выбранным CSV/XML.
Доступны создание, список, карточка, PATCH общих настроек и DELETE через ARCHIVED.
API принимает name/code/export_settings; schema/status/id/version клиента
при создании и schema/status при PATCH запрещены. Рабочая схема редактируется
отдельным API среза 1.3.3.

Таблица fb_feeds находится в tenant-схеме и хранит полные schema_definition и
export_settings JSONB без отдельных таблиц полей/правил/ревизий.
Feed.change_settings и Feed.archive возвращают новое проверенное frozen-состояние.
Версия конкурентного сохранения — FeedVersionVO: создаётся со значением 1,
увеличивается один раз при фактическом изменении; это не ревизия схемы.
Повтор одинаковых настроек не изменяет дату/версию и не пишет БД.

DELETE сохраняет строку и код. Архив исключён из обычного списка, доступен через
status=ARCHIVED и GET карточки, редактирование запрещено. Повтор DELETE архива
возвращает 204 даже с прежней положительной expected_version.
Отсутствующий ID, включая ID другого tenant, возвращает 404.

SQLAlchemy и query/write repositories используют существующий внешний UoW
на уже привязанном tenant-соединении. Сценарии не открывают транзакции и
не присваивают свойства агрегату. UUID и время получаются через существующие порты.
Фоновые задания, Outbox, public routes и хранение остальных агрегатов не создаются.

#### **1.3.3. Реализованный конструктор рабочей схемы**

Пользователь собирает состав товарного предложения в Console: STRING/TEXT/MONEY,
источники, локали/fallback, необязательная валютная метка, ограничения,
преобразования, порядок и участие в экспорте. Схема сохраняется целиком через
Feed.change_schema в fb_feeds.schema_definition и открывается повторно без потерь.
Новые поля создаются пользователем; обязательных системных title/sku/price нет.

Feed.version общий для схемы, настроек и архивации. Сохранённое определение сразу
становится актуальным для чтения и следующего запуска. В редакторе черновиком
называется локальный несохранённый ввод. Реализованы чистый evaluator,
редактирование IF/ELSE и предпросмотр MONEY на реальном SIMPLE/выбранном VARIANT.
API сохраняет полный AST. Сохранённый ассортимент описан в 1.3.4.

#### **1.3.4. Реализованный ассортимент FeedPublication**

В Console доступна вкладка «Товары»: выбор SIMPLE и конкретных VARIANT,
атомарное добавление до 100 явных ссылок, серверный список/поиск/статусы/страницы,
карточка и проверка цены существующим evaluator. Выбор «Всех существующих»
фиксирует ограниченный набор ID; новые варианты автоматически не подключаются.
Публикации хранятся в fb_publications отдельно от Feed. Повторные и конкурентные
добавления возвращают прежний ID, сохраняя PAUSED/ARCHIVED и overrides.
Пауза/возобновление/архивация/явный возврат выполняются через Domain и собственную
версию Publication; Feed.version и статус Feed от изменения состава не меняются.
Пустая схема и отсутствие цены не блокируют привязку. Архивный Feed read-only.
Полный расчёт полей и пробный CSV описаны в 1.3.5 и 16.6.2.

#### **1.3.5. Реализованный расчёт публикаций и пробный CSV**

PublicationResolver разрешает STRING/TEXT/MONEY по сохранённой схеме Feed и
пакетным снимкам Catalog. Console показывает до 20 ENABLED-публикаций, а пробный
CSV использует весь ENABLED-ассортимент и те же итоговые значения. Блокирующая
ошибка публикации прерывает скачивание и указывает позицию и поле.

### **1.4. Границы контекстов**

```text
Catalog: простые товары, родители/варианты, эффективный контент, regular/sale/purchase price, категории и ревизии
reference_data: справочник поддерживаемых локалей
        ↓ публичные Application Ports
FeedBuilder: схема → условный расчёт поля / override → проекция
        ↓
ExportRecord staging → Generic CSV / Generic XML → Files (Storage)
        ↓
FeedExportState.active_file_id → HTTP Feed Builder на хосте tenant
```

Application читает Catalog через публичные контракты владельца, а чистый
Domain-вычислитель работает с неизменяемыми снимками. Источником проверок локалей
остаётся справочник reference_data, форму валютной метки проверяет CurrencyVO.
Согласование API-цен Channels с выгрузками — отдельный будущий контракт.

`price.purchase` — собственное необязательное поле `purchase_price` выбранного
SIMPLE или VARIANT в Catalog. Целевой пакетный снимок передаёт его вместе с другими
ценами позиции. См. [модель цен Catalog](catalog.md#цены-продаваемой-позиции).

### **1.5. Будущие пресеты**

Пресеты Prom, Rozetka и пользовательские пресеты будут предоставлять исходные
определения полей, формул и условий. Применение создаёт обычные поля с новыми
field_id/rule_id внутри конкретного Feed, а не живую ссылку на общий пресет.
Автоматическое обновление существующего Feed при изменении пресета не подразумевается.
Требования площадки проверяет FormatProfile; происхождение из пресета не даёт
полю особых привилегий. В первом срезе и текущем MVP пресеты не реализуются.

## **2. Архитектурные решения и обязательные требования**

| Вопрос | Решение |
| --- | --- |
| Корни ближайшего среза | Feed, FeedPublication, FeedExportState |
| Что хранит Feed | Пользовательскую схему, настройки экспорта и идентификатор публичной ссылки |
| Product Mode MVP | Только VARIABLE_TO_SINGLE, по умолчанию в export_settings |
| Состав выгрузки | Явно выбранные простые товары и конкретные варианты через FeedPublication |
| Представление вариантов | Одна самостоятельная запись на выбранный вариант, без строки родителя и группировки |
| Где определены наценки | В MoneyValueDefinitionVO конкретного MONEY-поля |
| Где хранятся правила | В актуальном определении FeedSchema в `fb_feeds.schema_definition` |
| Как выбирается правило | Первое совпадение в порядке массива; иначе default_expression |
| Что возвращает формула | Конечную денежную сумму до округления/constraints |
| Как представлены выражения | Типизированное декларативное дерево, не исполняемый текст |
| Где хранится ручное значение | Override публикации по field_id |
| Когда применяется изменение формулы | После сохранения в Feed, начиная со следующего запуска |
| Как создаётся файл | Один выбранный CSV либо XML в Files, активный file_id в FeedExportState |
| Что сохраняется при ошибке | Последний отчёт о проверке и прежний активный файл |
| Как устроена выдача | Один заменяемый идентификатор ссылки внутри Feed, маршрут на хосте tenant |
| С чего начинается реализация | Только Domain-объекты Feed с create/restore |

### **2.1. Definition, Override и Resolved Value**

Definition — описание поля в схеме Feed: тип, источник/расчёт, язык,
валюта, условия, выражения, fallback, constraints, transforms и экспорт.
Override — индивидуальное значение конкретной публикации без копии остальных
данных товара. Resolved Value — итог после автоматического определения либо
ручного ввода, округления и проверки. Эти модели не подменяют друг друга.

### **2.2. Архитектурный перечень для проверки всего diff**

Нормативные документы: [backend](../architecture/backend.md) и
[frontend](../architecture/frontend.md). Требования проверяются по объёму среза:

1. Структура: модуль → слой → Aggregate Root → ответственность. Дочерние Entity
   поля и правила хранятся в границе своего агрегата. `FeedExportState` получает
   собственный repository; файл доступен по публичному контракту Files. Общие SQL-модели
   расположены в infrastructure/persistence/models.
2. Domain — обычный Python без FastAPI, Pydantic, SQLAlchemy, I/O и logger.
   Фабрики агрегата/Entity create/restore явные; __post_init__ допустим только VO.
   В объектном срезе других методов поведения нет. В последующих срезах состояние
   меняется через domain-методы, не присваивания из Application.
3. VO неизменяемы глубоко: typed tuples/frozensets и вложенные VO вместо mutable
   dict/list. Каждый VO — отдельный файл; package __init__.py пустые.
   Все методы аннотированы, docstrings публичных контрактов пишутся по-русски.
4. Локальное значение проверяет VO, состав/согласованность агрегата — его фабрика
   и будущие методы. Инварианты не переносятся в mapper. Restore не создаёт новые
   ID, не подставляет демонстрационные поля и не создаёт события повторного создания.
5. В следующих срезах write repository contracts принадлежат Domain, read/query
   и external ports — Application. Query не восстанавливает агрегаты ради таблицы.
   Каждый сценарий имеет Command/Query, Handler и собственный результат DTO либо None.
6. UoW открывается во внешней сборке Depends/worker; репозитории атомарного процесса
   используют одну сессию. Application не получает AsyncSession/uow_factory.
   Outbox записывается до общего commit; доставка выполняется отдельно после него.
7. HTTP controller/request/response каждого метода — отдельные файлы; router
   регистрирует маршруты, Depends собирает зависимости. Identity/Tenancy работают
   через существующие доверенные границы; пользователь не выбирает SQL-схему.
8. Application получает товарные данные Catalog и значения справочников
   через порты. Domain не импортирует чужие агрегаты.
   Вычисление не обращается к текущим часам, БД или внешнему API.
9. Frontend разделяет API/DTO/mapper, чистые модели, queries, mutations, page state,
   Page и UI. Общий HTTP client, Decimal-строки, AbortSignal; UI — props/emits.
10. Серверный кеш — TanStack Vue Query. Keys учитывают tenant и параметры;
    refetch не стирает отдельный draft, mutation очищает только отправленный snapshot.
    Смена tenant отменяет запросы и исключает поздние ответы старого контекста.
11. Цены/условия исполняет backend; frontend строит AST и отображает серверный preview.
    Права защищают исходные закупочные данные и их производные в trace/экспорте.
12. Логи содержат безопасные ID/коды и корреляцию, committed — после commit;
    токены, тела формул с чувствительными данными и закупочные значения не логируются.
13. Для документации проверяются ссылки, примеры, согласованность и весь diff.
    Сборка/БД/UI-тесты нужны при реализации соответствующих срезов, не при правке плана.

### **2.3. Целевая организация файлов**

```text
src/modules/feed_builder/
  domain/{feed,publication,export_state}/
  application/{feed,publication,export_state}/
    command/<scenario>/{command.py,handler.py,dto.py}
    query/<scenario>/{query.py,handler.py,dto.py}
    port/
  application/service/
  infrastructure/{feed,publication,export_state}/persistence/
  infrastructure/persistence/models/<table>.py
  infrastructure/{catalog,storage,serialization}/
  presentation/{feed,publication,export_state}/
    router.py, depends.py
    http/{controller,request,response}/<scenario>.py
  presentation/depends/
```

Объектный срез создаёт Domain из разделов 3.4 и 3.7–3.10.
Текущая вертикаль Feed добавляет необходимые файлы четырёх слоёв по разделу 1.3.2;
новые сценарии экспорта добавляются по объёму раздела 16.7.
Остальные каталоги появляются по факту реализации. Общие UoW/jobs/events/storage
механизмы переиспользуются; файловая структура не определяет границы агрегатов.

## **3. Domain: текущие объекты и будущие границы**

### **3.1. Aggregate Roots целевого модуля**

| Корень | Ответственность | Когда реализуется |
| --- | --- | --- |
| Feed | Определения полей, настройки и публичная ссылка | CRUD, редактор и ссылка реализованы |
| FeedPublication | Привязка позиции, участие, индивидуальные overrides | Реализовано |
| FeedExportState | Незавершённая задача, последний отчёт и один активный file_id | Заменяет объектную модель генерации в 16.7 |

FieldDefinition и ConditionalPriceRule — Entity внутри Feed. Отдельного корня
для наценок нет. FeedSchemaVO и настройки — VO. Проекция публикации — read model.
Связи самостоятельных агрегатов — по ID, не через Python-ссылки на чужой агрегат.

### **3.2. Feed: текущее состояние и минимальное поведение**

| Поле | Тип / смысл |
| --- | --- |
| id | FeedIdVO |
| name, code | FeedNameVO, FeedCodeVO |
| status | FeedStatus: DRAFT / ACTIVE / PAUSED / ARCHIVED; реализован переход в ARCHIVED |
| schema | FeedSchemaVO; допускает пустой состав |
| export_settings | FeedExportSettingsVO |
| version | FeedVersionVO: положительный BIGINT конкурентного сохранения |
| created_at, updated_at | Timezone-aware datetime |

Feed.create получает явные ID/время и обязательные export_settings с выбранным
форматом; создаёт пустую схему, если состав не передан. export_settings не имеет
значения по умолчанию и не принимает None. Feed.restore восстанавливает все
переданные значения, проверяет согласованность и не генерирует ID, события или
предзаполненные поля.
Новый Feed создаётся в DRAFT. Restore сохраняет явно переданное допустимое состояние.

Feed остаётся frozen. change_settings(name, code, export_settings, now) возвращает
новый Self, сохраняя id/created_at/schema/status, обновляя updated_at и version.
Все свойства типизированы и проверяются до возврата; архив редактировать нельзя.
archive(now) сохраняет схему/настройки и переводит в ARCHIVED с новой версией.
Повторное действие возвращает исходный объект. Время с timezone не может быть
раньше updated_at. Создание, обновление и restore не создают события этого среза.
В persistent mapper версия всегда берётся из row_version; missing/corrupt
сохранённые значения не заменяются defaults.

FeedExportSettingsVO содержит обязательное format_settings: ExportFormatSettings,
product_mode: FeedProductMode со значением VARIABLE_TO_SINGLE по умолчанию и
validation_policy: ValidationPolicy со значением STRICT по умолчанию.
ExportFormatSettings — закрытое объединение
`CsvExportSettingsVO | XmlExportSettingsVO` в types.py. Один Feed формирует ровно
один файл выбранного формата; для CSV и XML одновременно создаются два отдельных
Feed со своими ID/кодами и явно заданными настройками.

Каждый VO хранится в своём файле и определяет фиксированный формат класса:

| VO | ClassVar format | Собственные параметры |
| --- | --- | --- |
| CsvExportSettingsVO | ExportFormat.CSV | delimiter, encoding, include_header |
| XmlExportSettingsVO | ExportFormat.XML | root_name: ExportNameVO, item_name: ExportNameVO, encoding |

format не является полем конструктора; нельзя задать XML для CSV-настроек или
наоборот. Каждый VO проверяет собственные параметры. format_settings принимает
ровно один CsvExportSettingsVO либо XmlExportSettingsVO, без значения по умолчанию.
Без format_settings настройки не создаются, без export_settings не создаётся Feed.
Сырые Enum/строки/dict, None и коллекции любого размера отклоняются. Отдельных
formats/csv/xml-свойств нет; проверки количества и дубликатов форматов не нужны.
Настройки и вложенный VO неизменяемы, фабрики не выбирают формат за вызывающий код.

```python
FeedExportSettingsVO(
    format_settings=CsvExportSettingsVO(delimiter=";", include_header=True),
    product_mode=FeedProductMode.VARIABLE_TO_SINGLE,
)
```

Для XML вместо CsvExportSettingsVO передаётся один XmlExportSettingsVO с нужными
root_name/item_name. Выбранный формат доступен как
`feed.export_settings.format_settings.format`; дублирующий Enum на уровне Feed
или FeedExportSettingsVO не вводится. Пустая схема draft по-прежнему допустима.

FeedProductMode объявляется в отдельном enum/feed_product_mode.py:

```python
class FeedProductMode(StrEnum):
    """Определяет представление выбранных товаров в выгрузке."""

    VARIABLE_TO_SINGLE = "VARIABLE_TO_SINGLE"
```

VO проверяет в __post_init__, что product_mode — экземпляр FeedProductMode;
сырые строки, неизвестные значения и чужие Enum отклоняются с InvalidFeedValueError.
Будущая граница ввода явно преобразует код в Enum. Feed.create получает режим
из явно переданных настроек (product_mode в них имеет default); Feed.restore
сохраняет его без изменения остальных свойств. Product Mode принадлежит настройкам экспорта
Feed, применяется к выбранной выгрузке и не входит в FieldDefinition/FeedSchemaVO.
В первой версии нет выбора между стратегиями, отдельной схемы родителя,
настроек группировки или переключения режимов.

| Объект Catalog | Поведение VARIABLE_TO_SINGLE |
| --- | --- |
| SIMPLE | Одна публикация и самостоятельная экспортная запись |
| VARIABLE | Контекст родителя и выбор дочерних вариантов; собственной записи нет |
| VARIANT | Отдельная публикация и самостоятельная запись выбранного варианта |

Тип Catalog при этом не меняется. Настройки режима не определяют ассортимент:
конкретные позиции выбираются по правилам раздела 9.1. Одна схема полей применяется
ко всем продаваемым позициям, независимо от SIMPLE/VARIANT. Расширение Enum новыми
режимами относится к будущему срезу группировки; его поведение сейчас не реализуется.

Текущее поведение Feed включает change_settings/change_schema/archive.
change_schema(schema, now) проверяет структуру и совместимость прямых источников
через Policy и атомарно возвращает новое frozen-состояние. ID/created_at/настройки
сохраняются; при фактическом изменении увеличивается Feed.version и updated_at.
No-op не пишет БД. Архив и время ранее updated_at отклоняются. Следующая
генерация получает сохранённое рабочее определение Feed.
Код уникален в пределах tenant на persistence/application уровне;
VO проверяет только формат. FeedCode не используется как публичный секрет.

### **3.3. Зависимые Entity и определения значений**

FieldDefinition содержит только общие свойства: id: FieldIdVO, key: FieldKeyVO,
label: FieldLabelVO, type_definition: FieldTypeDefinition,
export: FieldExportSettingsVO и необязательные ai_instruction-метаданные.
Типозависимых свойств value_type/locale/currency/value_definition/constraints/
fallback_policy/transforms на верхнем уровне Entity нет.

FieldTypeDefinition — закрытое типизированное объединение
`StringFieldTypeVO | TextFieldTypeVO | MoneyFieldTypeVO`, а не dict или массив
произвольных параметров. Каждый VO хранится в отдельном файле:

| VO | Собственные настройки |
| --- | --- |
| StringFieldTypeVO | kind=STRING, value_definition: TextValueDefinition, locale: LocaleCodeVO или None, fallback_policy: LocaleFallbackPolicyVO или None, constraints: TextConstraintsVO, transforms: tuple[TransformDefinitionVO, ...] |
| TextFieldTypeVO | kind=TEXT, тот же состав текстовых настроек для длинного текста |
| MoneyFieldTypeVO | kind=MONEY, currency: CurrencyVO либо None (по умолчанию), value_definition: MoneyValueDefinitionVO, constraints: MoneyConstraintsVO, transforms: tuple[TransformDefinitionVO, ...] |

kind — фиксированная ClassVar класса VO, не вход конструктора и не отдельный
изменяемый enum поля. Например, SKU — StringFieldTypeVO с locale=None;
локализованный заголовок — StringFieldTypeVO с locale; описание — TextFieldTypeVO;
цена — MoneyFieldTypeVO с необязательной currency. Ключ не определяет тип или доступные настройки.
У текстовых VO нет currency, у денежного — locale/fallback_policy.

TextValueDefinition — объединение SourceValueDefinitionVO и ManualValueDefinitionVO:

- SourceValueDefinitionVO: kind=SOURCE, source: SourceReferenceVO. Для STRING/TEXT.
- ManualValueDefinitionVO: kind=MANUAL. Для STRING/TEXT без автоматического источника.
- MoneyValueDefinitionVO: kind=MONEY, mode=SOURCE / CALCULATED / MANUAL.
  Принадлежит MoneyFieldTypeVO; содержит либо source, либо calculation, либо ни того
  ни другого для ручного ввода. Два автоматических способа одновременно запрещены.

У MONEY currency необязательна и не влияет на сумму. Источник метку не заполняет.
Для локализованного источника текста нужна locale; для языконезависимого
допускается None. Форма locale/currency
проверяется VO; языковые требования внешнего источника — будущим
Application. Fallback требует целевую locale и не повторяет её в цепочке.
value_definition внутри соответствующего типа задаёт один способ получения значения.

SourceReferenceVO — неизменяемая ссылка с provider: SourceProvider и
path: CatalogSourcePath. В первом срезе поддерживается только
SourceProvider.CATALOG; допустимые пути закрыты Enum:

| CatalogSourcePath | Стабильный код | Назначение |
| --- | --- | --- |
| TITLE | item.title | Короткий локализованный текст |
| DESCRIPTION | item.description | Длинный локализованный текст |
| SKU | item.sku | Языконезависимая строка |
| REGULAR_PRICE | item.regular_price | Числовая сумма обычной цены без наследования валюты |

Пример Domain-ссылки:
`SourceReferenceVO(provider=SourceProvider.CATALOG, path=CatalogSourcePath.TITLE)`.
VO принимает только экземпляры нужных Enum, проверяет соответствие пути провайдеру
в __post_init__ и не преобразует строки автоматически. Даже строки "catalog" и
"item.title", а также чужие Enum с совпадающими кодами отклоняются с
InvalidFeedValueError. Произвольные пути/URL/выражения не входят в контракт.
Enum принадлежат FeedBuilder, не импортируют Domain Catalog и задают логические
идентификаторы потребителя, а не Python-атрибуты или SQL-колонки владельца.

Будущие границы ввода/хранения явно преобразуют строковые коды в Enum до создания
SourceReferenceVO. В JSON сохраняются прежние provider/path коды, формат схемы
остаётся 1. Существование адаптера, права, тип результата и требование locale
проверяются через SourcePathRegistry/Application по мере подключения исполнения.
Текущий конструктор уже проверяет тип/локаль прямого источника и доступность
локалей через owner-порт справочника; данные товаров не читаются. Domain
источники не читает. Новый встроенный путь/провайдер требует явного расширения
Enum и проверки допустимой пары; пользователь не регистрирует произвольный path.
Для будущих пользовательских характеристик вводится отдельная типизированная
ссылка по ID характеристики в соответствующем срезе.

Целевой PriceCalculationVO содержит упорядоченный
`tuple[ConditionalPriceRule, ...]` и обязательное default_expression.
При пустом списке правил всегда используется default_expression. Закупочная
цена представлена ссылкой на параметр `price.purchase` в AST.
ConditionalPriceRule содержит id: PriceRuleIdVO, condition и expression.
Порядок определяется массивом, отдельного конфликтующего priority нет.

У FieldDefinition и ConditionalPriceRule только create/restore. Их идентичность
сохраняется при восстановлении; новый объект получает явно переданный ID.
Они не загружаются и не изменяются независимо от Feed.

FeedSchemaVO содержит tuple неизменяемых определений полей и schema_format_version.
Цена/условия/выражения сравниваются и сохраняются по полному состоянию, а не только
по ID дочерних Entity; при восстановлении сохраняются состав и порядок.
Все входные коллекции копируются в неизменяемые структуры, наружу не выходит
mutable ссылка, способная изменить агрегат в обход будущих domain-методов.

### **3.4. Файлы первого среза: каждый VO отдельно**

Дерево показывает Domain-основу Feed в целевом плане.

```text
src/modules/feed_builder/domain/feed/
  aggregate.py
  error.py
  entity/
    field_definition.py
    conditional_price_rule.py
  policy/
    price_calculation_structure.py   PriceCalculationStructurePolicy
  value_object/
    feed_id.py                       FeedIdVO
    feed_version.py                  FeedVersionVO конкурентного сохранения
    feed_name.py                     FeedNameVO
    feed_code.py                     FeedCodeVO
    field_id.py                      FieldIdVO
    field_key.py                     FieldKeyVO
    field_label.py                   FieldLabelVO
    locale_code.py                   LocaleCodeVO
    export_name.py                   ExportNameVO
    source_reference.py              SourceReferenceVO
    source_value_definition.py       SourceValueDefinitionVO
    manual_value_definition.py       ManualValueDefinitionVO
    money_value_definition.py        MoneyValueDefinitionVO
    string_field_type.py             StringFieldTypeVO
    text_field_type.py               TextFieldTypeVO
    money_field_type.py              MoneyFieldTypeVO
    text_constraints.py              TextConstraintsVO
    money_constraints.py             MoneyConstraintsVO
    locale_fallback_policy.py        LocaleFallbackPolicyVO
    field_export_settings.py         FieldExportSettingsVO
    transform_definition.py          TransformDefinitionVO
    truncate_parameters.py           TruncateParametersVO
    money_ceil_step_parameters.py    MoneyCeilStepParametersVO
    feed_schema.py                   FeedSchemaVO
    feed_export_settings.py          FeedExportSettingsVO
    csv_export_settings.py           CsvExportSettingsVO
    xml_export_settings.py           XmlExportSettingsVO
    price_rule_id.py                 PriceRuleIdVO
    price_calculation.py             PriceCalculationVO
    parameter_reference.py           ParameterReferenceVO
    decimal_literal.py               DecimalLiteralVO
    price_amount.py                  PriceAmountVO: точная сумма без валюты
    scalar_literal.py                ScalarLiteralVO
    collection_literal.py            CollectionLiteralVO
    arithmetic_expression.py         ArithmeticExpressionVO
    function_expression.py           FunctionExpressionVO
    comparison_condition.py          ComparisonConditionVO
    logical_condition.py             LogicalConditionVO
    presence_condition.py            PresenceConditionVO
  enum/
    feed_product_mode.py
    source_provider.py
    catalog_source_path.py
    feed_status.py
    field_value_type.py
    value_definition_kind.py
    money_value_mode.py
    locale_fallback_mode.py
    transform_operation.py
    arithmetic_operator.py
    presence_operator.py
    literal_value_type.py
    comparison_operator.py
    logical_operator.py
    price_function.py
    export_format.py
    validation_policy.py
  types.py                           Aliases узлов, типов полей и ExportFormatSettings
  limits.py                          Структурные бюджеты определений
  validation.py                      Проверки значений и типов узлов
  field_type_validation.py           Общие чистые проверки текстовых настроек/transforms
```

CurrencyVO переиспользуется из shared как необязательная метка;
MoneyVO в FeedBuilder не используется. FeedIdVO/FieldIdVO/PriceRuleIdVO
строятся на существующем EntityIdVO. Новый LocaleCodeVO локален FeedBuilder и
не импортирует внутренний LocaleVO/ошибки Catalog. DTO и repository добавлены
только для Feed CRUD; events, policies исполнения и evaluator пока отсутствуют.
types.py не объединяет
определения VO.

Собственные настройки и допустимые операции проверяет соответствующий VO типа
в __post_init__: текст принимает только string.trim/string.truncate, MONEY —
money.ceil_step. Общие проверки двух текстовых VO и замораживание transforms
находятся в field_type_validation.py, без проверки инвариантов всего Feed.
Несовместимые наборы свойств исключены составом типов, оставшиеся проверки
принадлежат самим VO; отдельная Policy совместимости поля не нужна.
PriceCalculationStructurePolicy проверяет ID правил, глубину и число узлов. Её вызывает
FieldDefinition.restore для вложенного CALCULATED; create делегирует restore.
Feed.restore повторно восстанавливает дочерние Entity и проверяет уникальность
полей/ключей/экспортных имён. Эти инварианты не переносятся в VO или mapper.
UUID-литералы условий в Domain представлены EntityIdVO; JSON UUID-строки
преобразуются на будущей границе ввода. Сырые UUID-аннотации в Domain не вводятся.

### **3.5. Constraints, transforms и числовые значения**

TextConstraintsVO: required=False по умолчанию, min_length/max_length — целые
неотрицательные длины, min ≤ max. Принадлежит StringFieldTypeVO/TextFieldTypeVO.
MoneyConstraintsVO: required=False, min_amount/max_amount — конечные Decimal,
min ≤ max. Принадлежит MoneyFieldTypeVO. Денежные границы и длины не объединяются
в один объект с условно применимыми свойствами.
Ни required, ни тип MONEY не вводят обязательного поля по специальному ключу.

Transforms MVP: string.trim, string.truncate, money.ceil_step. Порядок — порядок
массива type_definition.transforms, максимум 128 определений. Входной список
копируется в tuple. Trim без параметров, truncate с TruncateParametersVO, ceil_step с
MoneyCeilStepParametersVO и положительным конечным Decimal. Сейчас моделируются
только определения, исполнение появится в вычислительном срезе.

PriceAmountVO хранит точный конечный Decimal без валюты и неявного округления.
Применяется к ручным значениям публикации; типизированные выражения используют
DecimalLiteralVO, а не PriceAmountVO в качестве узла AST. Общая проверка суммы
ограничивает число значащих цифр до MAX_LITERAL_DIGITS=40 и модуль экспоненты до
MAX_LITERAL_EXPONENT=128. Ноль и отрицательные суммы допустимы; границы задаёт поле.
Исходные значения и все дробные разряды сохраняются, включая 6 знаков Catalog.
Shared MoneyVO не используется внутри FeedBuilder и не изменяется.
Будущий evaluator работает с Decimal, округление задаётся явным числовым
контрактом/преобразованиями, а не валютной меткой или точностью Shared MoneyVO.

### **3.6. Состояние Feed и публичная ссылка**

В MVP `schema` и `export_settings` содержат актуальное сохранённое определение.
В Feed хранится `public_link_id`. Отдельный агрегат или реестр публичных
ссылок для ближайшего среза не требуется. Domain-метод `rotate_public_link()`
принимает новый ID и меняет ссылку с проверкой версии Feed. ID первого адреса
присваивается при первой успешной публикации файла. Обновления содержимого
используют тот же ID.

В DRAFT и ACTIVE можно запросить пересборку при пригодной конфигурации.
Первая публикация файла переводит DRAFT в ACTIVE в одной транзакции.
PAUSED сохраняет выдачу и блокирует новые запуски. ARCHIVED закрывает выдачу.
Право на замену активного файла проверяется по состоянию Feed и `FeedExportState`.

### **3.7. FeedPublication и будущая готовность**

Publication хранит id: FeedPublicationIdVO, feed_id: FeedIdVO,
product_reference: CatalogProductReferenceVO, status: PublicationStatus,
overrides: tuple[FieldOverrideVO, ...], created_at, updated_at и
version: FeedPublicationVersionVO. Версия — положительный BIGINT, а не ревизия схемы.
CatalogProductReferenceVO содержит catalog_item_id: EntityIdVO и
catalog_variant_id: EntityIdVO | None. Ссылка на Catalog однозначна:

- Для SIMPLE: catalog_item_id — ID простого товара, catalog_variant_id=None.
- Для VARIANT: catalog_item_id — ID родительского VARIABLE, catalog_variant_id —
  ID выбранного варианта. Оба ID различны; принадлежность проверяется через Catalog.
- VARIABLE без выбранного варианта не является продаваемой публикацией.

FeedPublication — отдельный Aggregate Root со ссылкой на Feed по ID;
он не вкладывается в Feed.publications. В первой версии не создаются публикации
семейств/родителей. У каждого выбранного варианта свои status, overrides и ID
публикации, сохраняемые между генерациями и повторными добавлениями.
Запись override содержит
mode=MANUAL и value; отсутствие записи включает автоматическое определение поля.
Для MANUAL-поля отсутствие override означает отсутствие значения.

FieldOverrideVO содержит field_id: FieldIdVO и value: str | PriceAmountVO | None.
Единственный mode=OverrideMode.MANUAL фиксирован ClassVar и не передаётся
конструктору. Явный None не равен отсутствию записи: автоматический источник
не подменяет явно пустое значение. Пустой/многострочный текст допустим;
совместимость с required/типом схемы проверяется будущим поведением; валюта в override не дублируется.

create требует ID, feed_id, ссылку и now, создаёт ENABLED без overrides с version=1.
restore сохраняет все свойства, требует явную FeedPublicationVersionVO и типизированный статус, timezone-aware
даты с updated_at >= created_at, уникальные field_id и не более MAX_FIELDS
overrides. Входной list/tuple копируется в tuple. Restore не требует текущую
схему: после её изменения исторический override не теряется и не удаляется молча.
Существование Catalog/Feed, принадлежность варианта и уникальность публикаций
проверяются через Application/хранение, без I/O в Domain. Методы enable/pause/
archive/restore_participation возвращают неизменяемое новое состояние; no-op
сохраняет исходный объект, версию и updated_at. restore_participation — бизнес-
возврат из архива, отдельный от фабрики restore. Переходы сохраняют ссылку,
created_at и все overrides; прямого переназначения публикации другому товару нет.
Проверка Feed/режима вынесена в чистую PublicationParticipationPolicy.
Существующий DRAFT можно включить, обычный create сразу создаёт ENABLED.
Из ARCHIVED нельзя выполнить enable/pause: используется явный возврат.

PublicationStatus: DRAFT / ENABLED / PAUSED / ARCHIVED.
Readiness: READY / NEEDS_INPUT / INVALID / STALE. Это разные измерения.
Readiness и постоянные проекции в срезе управления ассортиментом не создаются.
Ни статус ENABLED, ни успешный расчёт одного поля не заменяют полную готовность.

- NEEDS_INPUT: нет обязательного ручного/текстового значения, перевода либо
  MANUAL_REQUIRED требует ручного перевода, при отсутствии более серьёзных ошибок.
- INVALID: ошибка вычисления, нужного параметра, типа, transform
  или constraints. Необязательность поля не скрывает ошибку выбранного расчёта.
- READY: нет блокирующих issues, обязательные значения корректны.
- STALE: сохранённая проекция устарела; не результат текущего вычисления.

Источник технически недоступен — отдельный сбой зависимости, не пустое значение.
Валидный override не требует получения параметров для автоматического
расчёта этого поля. С STRICT ошибка ENABLED-публикации блокирует весь новый файл;
молчаливое исключение товаров запрещено.

### **3.8. FeedExportState — одно состояние на Feed**

`FeedExportState` заменяет `FeedGeneration` и его `FeedArtifact`. Идентификатор
состояния — `feed_id`. При первом запросе на пересборку создаётся одна запись
экспорта. Последующие запросы обновляют её. Текущая задача, последний отчёт
и ссылка на активный файл хранятся в этой записи.

| Часть | Данные |
| --- | --- |
| Текущая пересборка | `job_id`, статус `PENDING` или `RUNNING`, время запроса и начала, снимок сохранённых схемы и настроек, версия движка, `as_of` после первого запуска |
| Последний отчёт | `completed_at`, `as_of`, политика проверки, итог `PUBLISHED` / `REJECTED` / `FAILED`, код результата, счётчики `total_items`, `valid_items`, `warning_items`, `rejected_items` и признак полного прохода |
| Активная выдача | `active_file_id`, фактический формат CSV/XML, `active_as_of` и `active_published_at` |

До первой успешной сборки активная выдача отсутствует. Незавершённая задача,
отчёт и активный файл могут относиться к разным обновлениям. Новая задача
сохраняет видимым последний завершённый отчёт. Завершение заменяет отчёт и
освобождает снимок задачи. Диагностики последнего отчёта читаются отдельно с
пагинацией по позициям. Ревизии запусков, последовательные номера и коллекция
исторических файлов в модель экспорта не входят.

Domain-методы регистрируют одну незавершённую задачу, начинают обработку,
фиксируют `as_of`, принимают результат проверки и условно заменяют ссылку
на активный файл. Методы проверяют `job_id`, состояние и согласованность
счётчиков. По завершённому проходу `total_items = valid_items + warning_items + rejected_items`.
При техническом сбое отчёт может содержать частичные счётчики и признак
неполного прохода. Срок аренды и повторы принадлежат `scheduled_jobs`.
Внешний worker проверяет актуального владельца задачи перед записью.

`active_file_id` указывает на `StoredFile` через контракт Files. Domain хранит
типизированный идентификатор и свойства активной выдачи. Files владеет байтами,
именем, MIME, размером и физическим ключом. Хранилище и потоковая выдача
находятся за пределами Domain.

### **3.9. Приватный доступ — последующий срез**

Ближайший срез вводит публичную ссылку Feed. Будущий PRIVATE использует
`FeedAccessKey` для независимого выпуска и отзыва нескольких токенов одного
фида. Отдельный токен передаётся как `?token=…` и проверяется только в PRIVATE.
Публичный идентификатор ссылки относится к Feed и заменяется независимо от
ключей. Выпуск, хранение digest и отзыв описываются в отдельном срезе.

### **3.10. Файлы текущего объектного среза**

```text
domain/
  error.py, validation.py
  feed/policy/schema_structure.py
  publication/
    aggregate.py, error.py
    enum/{publication_status,override_mode}.py
    value_object/{feed_publication_id,catalog_product_reference,field_override}.py
  generation/
    aggregate.py, error.py
    enum/generation_status.py
    entity/feed_artifact.py
    value_object/
      feed_generation_id.py, feed_artifact_id.py, generation_attempt_token.py
      generation_sequence.py, calculation_engine_version.py
      generation_definition_snapshot.py, generation_calculation_context.py
      generation_attempt.py, generation_counts.py, generation_failure.py
      artifact_storage_key.py, artifact_content_type.py, artifact_checksum.py
  access_key/
    aggregate.py, error.py
    enum/access_key_status.py
    value_object/{feed_access_key_id,access_token_hash}.py
```

Дерево показывает предыдущий объектный срез до замены модели генерации.
Контекстные ошибки остаются в каталогах соответствующих агрегатов. Каждый VO имеет собственный файл,
package __init__.py пустые. Агрегаты и Entity frozen в объектном срезе;
изменения состояния через replace/присваивание из Application не вводятся.

## **4. Декларативная схема, источники и валидация**

### **4.1. Пример определения**

Ниже только пример пользовательской схемы из двух полей, а не стартовый набор.
Feed также может не содержать ни одного текстового или денежного поля.
Default-выражение даёт +15% к `price.regular`. Правило категории при наличии
закупочной цены даёт +25% к `price.purchase`. Схема хранит выражения в AST.
Тип поля и все его настройки вложены в type_definition; верхнего value_type нет.
Пример показывает целевую форму schema_format_version=1. Переход с текущей
формы сохранённых схем описан в 16.6.2.

```json
{
  "schema_format_version": 1,
  "root": {
    "key": "publication",
    "kind": "object",
    "fields": [
      {
        "id": "11111111-1111-4111-8111-111111111111",
        "key": "title_uk",
        "label": "Назва",
        "type_definition": {
          "kind": "string",
          "locale": "uk",
          "value": {
            "kind": "SOURCE",
            "source": {
              "provider": "catalog",
              "path": "item.title"
            }
          },
          "fallback_policy": {
            "mode": "NONE"
          },
          "constraints": {
            "required": true,
            "max_length": 160
          },
          "transforms": [
            {
              "op": "string.trim",
              "params": {}
            }
          ]
        },
        "export": {
          "enabled": true,
          "name": "title_uk"
        },
        "ai": {
          "instruction": null
        }
      },
      {
        "id": "33333333-3333-4333-8333-333333333333",
        "key": "partner_price",
        "label": "Партнёрская цена",
        "type_definition": {
          "kind": "money",
          "currency": "UAH",
          "value": {
            "kind": "MONEY",
            "mode": "CALCULATED",
            "calculation": {
              "rules": [
                {
                  "id": "77777777-7777-4777-8777-777777777777",
                  "condition": {
                    "kind": "logical",
                    "operator": "ALL",
                    "operands": [
                      {
                        "kind": "comparison",
                        "operator": "CONTAINS",
                        "left": {
                          "kind": "parameter",
                          "parameter": "product.category_ids"
                        },
                        "right": {
                          "kind": "scalar",
                          "value_type": "uuid",
                          "value": "66666666-6666-4666-8666-666666666666"
                        }
                      },
                      {
                        "kind": "presence",
                        "operator": "EXISTS",
                        "parameter": "price.purchase"
                      }
                    ]
                  },
                  "expression": {
                    "kind": "arithmetic",
                    "operator": "MULTIPLY",
                    "left": {
                      "kind": "parameter",
                      "parameter": "price.purchase"
                    },
                    "right": {
                      "kind": "decimal",
                      "value": "1.25"
                    }
                  }
                }
              ],
              "default_expression": {
                "kind": "arithmetic",
                "operator": "MULTIPLY",
                "left": {
                  "kind": "parameter",
                  "parameter": "price.regular"
                },
                "right": {
                  "kind": "decimal",
                  "value": "1.15"
                }
              }
            }
          },
          "constraints": {
            "required": true,
            "min_amount": "0"
          },
          "transforms": [
            {
              "op": "money.ceil_step",
              "params": {
                "step": "0.1"
              }
            }
          ]
        },
        "export": {
          "enabled": true,
          "name": "partner_price"
        },
        "ai": {
          "instruction": null
        }
      }
    ]
  }
}
```

Для прямого MONEY-источника type_definition.value имеет вид:

```json
{"kind": "MONEY", "mode": "SOURCE", "source": {"provider": "catalog", "path": "item.regular_price"}}
```

Для суммы без валютной метки currency можно опустить либо передать null:

```json
{
  "kind": "money",
  "currency": null,
  "value": {
    "kind": "MONEY",
    "mode": "SOURCE",
    "source": {"provider": "catalog", "path": "item.regular_price"}
  }
}
```

Числовая сумма источника сохраняется; его валюта не наследуется. CurrencyVO
нормализует трёхбуквенный код в верхний регистр; пустая строка не заменяет None.

Для ручного MONEY: `{"kind":"MONEY","mode":"MANUAL"}`; для ручного текста:
`{"kind":"MANUAL"}`. У текстового SOURCE источник находится в type_definition.value.source.
Неактивные варианты source/calculation отсутствуют; неизвестные свойства и
смешанные варианты отклоняются. JSON-имя type_definition.value соответствует
Domain-свойству type_definition.value_definition. В JSON kind передаётся как
дискриминатор string/text/money/integer/boolean; mapper выбирает класс VO и не передаёт
kind в его конструктор. Денежный value.kind=MONEY обозначает определение значения,
а type_definition.kind=money — класс типа поля; противоречивый вариант отклоняется.
JSON-коды source.provider/source.path соответствуют значениям SourceProvider и
CatalogSourcePath. На границе ввода они явно преобразуются в нужные Enum;
неизвестные значения отклоняются до создания Domain-объекта.

### **4.2. Свойства и локализация**

| Свойство | Смысл |
| --- | --- |
| id | Стабильный field_id, не зависит от порядка/названия |
| key / label | Уникальный внутренний ключ / подпись |
| type_definition.kind | string / text / money / integer / boolean, определяет класс VO |
| type_definition.locale | Только STRING/TEXT, локаль либо null для языконезависимого текста |
| type_definition.currency | Только MONEY, необязательный код результата; null не наследует валюту источника |
| type_definition.value | Один типизированный способ получения значения |
| type_definition.fallback_policy | Только STRING/TEXT, явная политика отсутствующих переводов |
| type_definition.constraints | Обязательность, границы длины, суммы или целого числа по типу |
| type_definition.transforms | Допустимые данному типу упорядоченные преобразования |
| export.enabled / name | Участие в выгрузке / имя колонки, XML-элемента или XML-атрибута |
| export.xml_placement | `ELEMENT` по умолчанию или `ATTRIBUTE` в открывающем теге предложения |
| ai.instruction | Только метаданные будущего сценария |

Текстовые пути item.title/item.description не содержат языка; locale передаётся
в текстовом type_definition. NONE не подставляет другой перевод, LOCALE_CHAIN последовательно
проверяет заданные locales после целевой, MANUAL_REQUIRED требует ручного значения
при отсутствии целевого перевода. Фактическая локаль возвращается preview.
Цепочки конечны и не рекурсивны; языконезависимый текст не имеет fallback.

STRING и TEXT поддерживают `CONSTANT` со строкой в `type_definition.value.value`.
Этот текст используется во всех публикациях фида и проходит текстовые преобразования
и проверку длины. Для отдельной публикации можно задать переопределение. Например,
константа `r` с именем экспорта `selling_type` и размещением `ATTRIBUTE` даст
`<offer selling_type="r">` в XML.

INTEGER поддерживает остаток из Catalog, константу и ручное значение в публикации.
Его необязательные `min_value` и `max_value` включаются в допустимый диапазон.
API и Console поддерживают точные целые от −9 007 199 254 740 991 до 9 007 199 254 740 991.
BOOLEAN поддерживает наличие из Catalog, константу, ручное значение и вычисление
с `condition`, `then_value` и `else_value`. В IF доступны вложенные AND / OR,
сравнения параметров Catalog и проверка `EXISTS` для отсутствующих значений.
Типы `0` и `false` сохраняются в схеме, предпросмотре и overrides.
В CSV и XML логические значения записываются как `true` и `false`.

### **4.3. Структурная и семантическая проверка**

Первый Domain-срез проверяет собственные значения VO и согласованность
конструируемого Feed/Entity: типы, конечные числа, диапазоны, формы ID,
уникальность field_id/key/export.name и rule_id в пределах поля, порядок,
допустимые сочетания MONEY/text, структуру дерева/арность операций.
Прямые источники принимают только SourceProvider/CatalogSourcePath; неизвестный
или нетипизированный источник отклоняется уже при создании SourceReferenceVO.
Пустая схема допустима. Ошибка create/restore не создаёт частично валидный объект.

Feed хранит структурно корректное определение. Ранее сохранённые определения могут
содержать семантические ошибки, например ссылку на ещё не подключённый параметр.
Неизвестный provider/path отклоняется при сохранении. Незавершённое дерево остаётся
локальным черновиком Console. Перед постановкой генерации проверяются:

- Совместимость типов источников/параметров с полем, условиями и выражениями.
- Конечный числовой Decimal результата; валютная метка не участвует в арифметике.
- Известные операции, функции и точные схемы их параметров; обязательный ELSE.
- Допустимость операций для чисел, коллекций и UUID/строк/boolean.
- Поддержка локалей и прав на источник через справочники/Application Ports; форма необязательного кода валюты — через CurrencyVO.
- Хотя бы одно экспортируемое поле для Generic-профиля; безопасные XML-имена.
- Лимиты размера JSON, числа полей/правил/узлов, глубины AST, длины строк и
  числа операндов. Лимит байтов проверяется до декодирования на границе входа.

Чистые проверки находятся в Domain, получение внешних метаданных/прав — в
Application. Примеры title/price не создают скрытых проверок по ключу.
Совместимость типа и локали существующего `field_id` проверяется при изменении
сохранённой схемы. Значения товаров и overrides проверяются при resolve.

## **5. Infrastructure Layer — PostgreSQL**

### **5.1. Состав SQL-моделей**

| Таблица | Ответственность |
| --- | --- |
| `fb_feeds` | Схема, настройки и идентификатор публичной ссылки |
| `fb_publications` | Привязки товаров и overrides |
| `fb_publication_projections` | Вычисленные значения и готовность, отдельный срез |
| `fb_export_states` | Одна строка на Feed с текущей задачей, последним отчётом и активным file_id |
| `fb_export_issues` | Ошибки и предупреждения только последнего отчёта |

Таблицы экспорта и `fb_feeds.public_link_id` добавляет tenant-миграция
`0026_fb_export_state`. Готовые файлы регистрируются в существующих таблицах
Files и доступны в Storage.

### **5.2. Таблица Feed**

```
CREATE TABLE fb_feeds (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(64) NOT NULL,
    status VARCHAR(16) NOT NULL,
    row_version BIGINT NOT NULL,
    schema_definition JSONB NOT NULL,
    export_settings JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_fb_feeds_code UNIQUE (code),
    CONSTRAINT ck_fb_feeds_name CHECK (char_length(btrim(name)) BETWEEN 1 AND 255),
    CONSTRAINT ck_fb_feeds_code CHECK (code ~ '^[a-z][a-z0-9_-]{0,63}$'),
    CONSTRAINT ck_fb_feeds_status CHECK (status IN ('DRAFT','ACTIVE','PAUSED','ARCHIVED')),
    CONSTRAINT ck_fb_feeds_version CHECK (row_version >= 1),
    CONSTRAINT ck_fb_feeds_dates CHECK (updated_at >= created_at),
    CONSTRAINT ck_fb_feeds_schema CHECK (jsonb_typeof(schema_definition) = 'object'),
    CONSTRAINT ck_fb_feeds_settings CHECK (jsonb_typeof(export_settings) = 'object')
);
CREATE INDEX ix_fb_feeds_status_updated ON fb_feeds(status, updated_at, id);

```

`export_settings` в MVP хранит параметры:

```json
{
  "format_settings": {
    "format": "csv",
    "delimiter": ",",
    "encoding": "utf-8",
    "include_header": true
  },
  "product_mode": "VARIABLE_TO_SINGLE",
  "validation_policy": "STRICT"
}
```

`STRICT` по умолчанию отклоняет публикацию нового файла при ошибке любой
позиции. `SKIP_INVALID` публикует прошедшие проверку позиции, включая позиции
с предупреждениями. Если все включённые позиции отклонены, сохраняется
прежний файл и обновляется отчёт.
`format_settings`, `product_mode` и `validation_policy` хранятся в одной
JSONB-колонке. При создании format_settings обязательно, defaults
применяются только к product_mode/validation_policy и параметрам выбранного VO.
Запись сохраняет полный снимок с явным format_settings.format и параметрами
одного формата; SQL-default для export_settings отсутствует.
Mapper преобразует product_mode в FeedProductMode, а format_settings.format выбирает
CsvExportSettingsVO/XmlExportSettingsVO; format не передаётся в конструктор VO.
При записи mapper явно берёт format.value из ClassVar: dataclass asdict сам по себе
ClassVar не добавляет. Готовые настройки передаются фабрике restore, собственные
инварианты проверяет Domain. Коллекция formats и отдельные csv/xml не поддерживаются;
persistence/API Feed CRUD реализованы без aliases старой формы.
Изменение формата или его параметров увеличивает row_version. Следующий запуск
получит новые настройки из Feed. `schema_format_version` обозначает формат
JSON-документа схемы и сохраняется при смене CSV/XML.

Текущая модель: infrastructure/persistence/models/feed.py.
Tenant-миграция 0020_feed_builder_crud следует за 0019_catalog_price_amounts,
проверена на новом tenant и при upgrade/downgrade существующего tenant.
Модель зарегистрирована в src/modules/tenant_persistence.py вместе с историческим
именем fb_feeds; autogenerate на head должен оставаться пустым.

В целевом контракте schema_definition хранит канонический документ раздела 4
с полным порядком полей, AI-метаданными, AST, constraints и transforms.
Application schema_document формирует документ результатов без I/O; Infrastructure
definition_mapper восстанавливает VO/Entity и контролирует входную форму/бюджеты.
FeedMapper.to_domain вызывает Feed.restore, который проверяет инварианты корня.
Строки Decimal не преобразуются в float; currency=None остаётся None.

Для текущего CRUD row_version соответствует Feed.version. UPDATE содержит ID
и ожидаемую версию в WHERE; ноль обновлённых строк означает конфликт.
get_for_update использует блокировку строки. Репозиторий не вызывает commit/rollback.
Именованное ограничение uq_fb_feeds_code переводится в FeedCodeConflictError;
остальные IntegrityError не маскируются. Архивный код остаётся занятым.

Миграция 0020 содержит рабочую схему и настройки Feed. Колонку `public_link_id`
и таблицы состояния экспорта добавляет миграция 0026.

### **5.3. Сохранённая схема и снимок генерации**

`SaveFeedSchemaDraft` заменяет `fb_feeds.schema_definition` целиком с проверкой
`Feed.version`. После commit это определение читают редактор, предпросмотр,
пробный CSV и запрос следующей генерации. Редактор хранит несохранённые правки
локально. `GetFeedSchema` читает сохранённое определение.

При обновлении `RequestFeedRefresh` читает схему и настройки из одного
состояния Feed. Снимок хранится в `FeedExportState` на время задачи и её
повторов. История редактирования и публикация выбранной ревизии схемы входят
в расширение из раздела 17.

### **5.4. FeedPublication — реализовано**

```
CREATE TABLE fb_publications (
    id UUID PRIMARY KEY,

    feed_id UUID NOT NULL
        REFERENCES fb_feeds(id),

    catalog_item_id UUID NOT NULL,
    catalog_variant_id UUID NULL
        CHECK (catalog_variant_id IS NULL OR catalog_variant_id <> catalog_item_id),

    status TEXT NOT NULL
        CHECK (status IN (
            'DRAFT', 'ENABLED',
            'PAUSED', 'ARCHIVED'
        )),

    overrides JSONB NOT NULL
        CHECK (jsonb_typeof(overrides) = 'object'),

    row_version BIGINT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_fb_publications_reference UNIQUE NULLS NOT DISTINCT (
        feed_id,
        catalog_item_id,
        catalog_variant_id
    )
);

CREATE INDEX ix_fb_publications_feed_status
ON fb_publications(feed_id, status);

```

Это определение рассчитано на PostgreSQL 15+. `NULLS NOT DISTINCT` предотвращает создание нескольких публикаций одного простого товара, для которого `catalog_variant_id IS NULL`.

В MVP catalog_variant_id используется функционально: NULL обозначает SIMPLE,
не-NULL — выбранный VARIANT указанного родителя VARIABLE. Уникальность пары
защищает и простые позиции, и варианты при повторном/конкурентном добавлении.
FK на внутренние таблицы Catalog не вводится. Тип товара, существование и
принадлежность варианта проверяются через публичный контракт Catalog;
собственные инварианты публикации остаются в Domain.

**Формат overrides:**

```
{
  "11111111-1111-4111-8111-111111111111": {
    "mode": "MANUAL",
    "value": "Хлорофіл NOW Foods, 473 мл"
  },
  "33333333-3333-4333-8333-333333333333": {
    "mode": "MANUAL",
    "value": {
      "amount": "650.00"
    }
  }
}

```

Если поле наследуется, запись в `overrides` не требуется.

В будущем `FieldOverride` может поддерживать дополнительные режимы: `CLEAR`, `EXPRESSION`, `GENERATED`, не меняя физическую модель.

Таблица создаётся миграцией 0021_feed_publications после 0020_feed_builder_crud.
Domain передаёт даты и версию явно. Репозитории используют существующий tenant UoW;
сперва блокируется Feed, затем публикация. Это сериализует добавление/архив Feed
и не позволяет дублям появиться при перекрывающихся пакетах. Запись статуса
меняет только status/row_version/updated_at и не перезаписывает JSON overrides.
Read-side читает проекции напрямую; список не вызывает Feed/Publication.restore.
Сортировка created_at DESC, id DESC. Поиск подписей/SKU выполняет Catalog и отдаёт
IDs; собственный query repository применяет UUID-array и серверную пагинацию.
Межмодульного SQL JOIN нет. Подписи обогащаются только для текущей страницы.

### **5.5. Материализованная проекция**

```
CREATE TABLE fb_publication_projections (
    publication_id UUID PRIMARY KEY
        REFERENCES fb_publications(id),

    feed_version BIGINT NOT NULL,
    publication_version BIGINT NOT NULL,

    catalog_revision TEXT NULL,
    source_revisions JSONB NOT NULL DEFAULT '{}',
    as_of TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ NULL,

    resolved_values JSONB NOT NULL DEFAULT '{}',
    field_states JSONB NOT NULL DEFAULT '{}',
    issues JSONB NOT NULL DEFAULT '[]',

    readiness TEXT NOT NULL
        CHECK (readiness IN (
            'READY', 'NEEDS_INPUT',
            'INVALID', 'STALE'
        )),

    computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_fb_projection_readiness
ON fb_publication_projections(readiness);

```

Здесь `resolved_values` — данные для списков и предпросмотра, но не источник истины.

`field_states` содержит происхождение каждого значения:

```
{
  "11111111-1111-4111-8111-111111111111": {
    "origin": "MANUAL",
    "status": "VALID"
  },
  "33333333-3333-4333-8333-333333333333": {
    "origin": "INHERITED",
    "status": "VALID"
  }
}
```

Проекция устаревает при несовпадении `Feed.version`, версии публикации,
ревизий фактических источников
или при наступлении valid_until. Метаданные получаются через публичные порты,
без JOIN к таблицам чужих контекстов. События ускоряют инвалидацию, а проверка
ревизий/времени защищает от пропущенных событий. Для значений с override
ненужные автоматические зависимости не создаются.

После сохранения Feed устаревание проекций вычисляется при чтении по
несовпадению версий. Пересчёт выполняется пакетами.

### **5.6. Текущее состояние экспорта и Files**

`fb_export_states.feed_id` одновременно PK и FK на `fb_feeds`. В строке
нормализованы три группы колонок:

| Группа | Колонки |
| --- | --- |
| Текущая задача | `job_id`, `job_status`, `requested_at`, `started_at`, `job_as_of`, `definition_snapshot` |
| Последний отчёт | `last_completed_at`, `last_as_of`, `last_validation_policy`, `last_outcome`, `last_reason_code`, `last_is_complete`, четыре счётчика по разделу 3.8 |
| Активная выдача | `active_file_id`, `active_format`, `active_as_of`, `active_published_at` |

JSONB используется для временного снимка схемы и настроек с версией
вычислителя. Колонки текущей задачи очищаются при терминальном завершении.
Состояние активной выдачи заполняется целиком. При завершении заменяются
последний отчёт и его `fb_export_issues` в одном tenant UoW. Строки диагностики
принадлежат `feed_id` и содержат severity, code, message, идентификаторы
публикации/поля/правила и путь выражения. Отдельного ключа исторического запуска
для запроса диагностик нет.

`active_file_id` — индексируемый UUID Files. Физический FK используется для
`feed_id` внутри Feed Builder. Межмодульная ссылка проверяется по существующему
контракту Files. В адаптере используются `UploadFileHandler` и
`GetFileContentHandler`. При привязке проверяется `ready` под блокировкой Files
в том же tenant UoW. Read-side Feed Builder предоставляет Files запрос
использования живых `active_file_id` через его `FileUsagePort`. Storage
использует уже зарегистрированный `StoredFile` и его метаданные.

В транзакции замены ставится отложенная очистка прежнего файла. Она выполняется
после commit через механизмы Files с повтором при сбое. Очистка проверяет
актуальные ссылки и учитывает уже открытые потоки. Временный результат и
осиротевший объект очищаются с проверкой текущей задачи и принадлежности
файла Feed Builder. См.
[контракт потребителя Files](../modules/files.md#контракт-потребителя).

### **5.7. Публичная ссылка на хосте tenant**

Tenant-миграция добавляет в `fb_feeds` nullable `public_link_id` с уникальностью
в схеме tenant. Существующие Feed получают ID при первом успешном экспорте.
Маршрут сначала получает tenant из текущего хоста через Tenancy, затем ищет
`public_link_id` в его схеме. Замена ID в транзакции Feed отключает старый
адрес. Публичный глобальный реестр не нужен. Таблицы приватных ключей
относятся к будущему срезу 16.8.

### **5.8. Контекст расчёта и ревизии источников**

Правила и AST хранятся в сохранённой схеме Feed. Редактирование выполняется
через SaveFeedSchemaDraft. При запуске полное определение копируется в снимок задания.
Поле schema_format_version определяет формат дерева, а calculation_engine_version
генерации — поддержанную семантику вычисления. Неподдерживаемая версия отклоняется.

В fb_publication_projections дополнительно сохраняются as_of, valid_until,
source_revisions: JSONB с ревизиями использованных данных Catalog, включая
версию выбранной позиции, от которой зависит `price.purchase`. valid_until —
ближайшая известная граница акции или другой временной зависимости.
На границе времени проекция STALE без ожидания события изменения товара.

При необходимости в staging текущей задачи сохраняются ID и ревизии
использованных данных Catalog, временные границы и выбранный rule_id.
Staging очищается после завершения задачи. Чувствительные суммы не копируются в общие логи.

FeedBuilder не имеет провайдера курсов, валюты вычислений или автоматической
конвертации. as_of фиксируется до первого расчёта и сохраняется для retry.
Пользовательский коэффициент хранится в AST: например, price.regular / 40 * 1.20.
Изменение коэффициента требует нового определения/задания; retry использует
прежний снимок формулы. Необязательная currency является только меткой поля.

`Feed.version` защищает конкурентное сохранение и служит меткой актуальности
проекций. При активации файла сравниваются схема и настройки экспорта снимка
с сохранёнными значениями Feed.

## **6. Application: целевые порты, сценарии и транзакции**

Реализованы Feed CRUD, рабочая схема, управление ассортиментом, overrides,
расчётный предпросмотр, пробный CSV, фоновое обновление CSV и публичный маршрут.

### **6.1. Контракты хранения и внешних данных**

Write contracts FeedRepositoryProtocol, FeedPublicationRepositoryProtocol,
FeedExportStateRepositoryProtocol принадлежат
Domain своих корней и работают с агрегатами. Схема и правила сохраняются
через границу Feed; репозитории
для каждого VO, поля, правила или таблицы не создаются.

| Application Port / Service | Назначение |
| --- | --- |
| FeedQueryRepositoryProtocol | Списки/детали Feed и метаданные схем |
| FeedPublicationQueryRepositoryProtocol | Карточки, страницы, фильтры, статистика |
| FeedExportStateQueryRepositoryProtocol | Текущее состояние, последний отчёт и его диагностики |
| PublicationProjectionPort | Условная запись и инвалидация проекций |
| CatalogProductReader | Batch простые позиции/выбранные варианты, принадлежность родителю, эффективный контент, regular/sale/purchase price, интервалы акций и ревизии |
| ProductParameterReaderPort | Batch зарегистрированные категории/SKU/другие параметры Catalog |
| ReferenceDataReaderPort | Поддержка локалей; код валютной метки не требует курсового сервиса |
| ParameterRegistryPort | Типы, nullability, права, источники разрешённых параметров |
| SourcePathRegistry / FieldTypeRegistry / TransformRegistry | Метаданные допустимых источников/типов/преобразований и выбор handlers |
| PriceExpressionResolver | Application-координация входов, вызов чистого evaluator |
| FeedSerializerRegistry / FormatProfileRegistry | Сериализаторы и профили |
| FeedExportFilesPort / ExportStagingPort | Загрузка и потоковое чтение через Files, временные проверенные записи |
| FeedRefreshJobPort | Постановка обновления через `ScheduleScheduledJobUseCase` в UoW запроса |
| ProjectionJobPort | Постановка задач обновления материализованных проекций |
| OutboxRepositoryProtocol | Интеграционные сообщения при наличии подписчиков |
| PublicFeedQueryRepositoryProtocol | Текущий адрес Feed и активный file_id в доверенном tenant |
| Clock | Явное время preview/первого запуска и проверки актуальности |

Source adapter скрывает конкретный модуль и возвращает immutable snapshot,
не ORM/чужой агрегат. Метаданные вычислений не дают права читать закрытую цену.
Публичный пакетный снимок Catalog передаёт `purchase_price` и категории.
Application FeedBuilder получает снимок через собственный порт и адаптер.

SourcePathRegistry описывает источники из закрытого контракта Domain:
тип результата, locale, доступ и обработчик. Он не разрешает произвольные строковые
provider/path в обход SourceReferenceVO и не дублируется отдельным списком UI.
Реестр, порты и адаптеры в первом Domain-срезе не создаются.

### **6.2. Команды: входы и результаты**

Сценарии исполняются в доверенном tenant/actor-контексте. У текущего Feed CRUD
авторизацию проверяет Presentation, репозитории привязаны к tenant внешнего UoW.
Каждый сценарий имеет Command, Handler и конкретный DTO результата либо None. Для существующих
объектов передаются нужные expected_version; HTTP Request/ORM не входят в контракт.

| Сценарий | Вход кроме контекста | Результат |
| --- | --- | --- |
| CreateFeed | name, code, export_settings | CreateFeedResultDTO: карточка пустого DRAFT и version |
| UpdateFeed | feed_id, expected_version, name/code/export_settings | UpdateFeedResultDTO: карточка с сохранённой схемой и version |
| ArchiveFeed | feed_id, expected_version | None |
| SaveFeedSchemaDraft — реализовано | feed_id, definition с полями и AST, expected_version = Feed.version | SaveFeedSchemaDraftResultDTO: feed_id, version, definition |
| AddCatalogItemsToFeed | feed_id, item_references: пары catalog_item_id/catalog_variant_id | AddCatalogItemsToFeedResultDTO: mapping каждой пары → publication_id |
| RemoveFeedPublication | publication_id, expected_version | None |
| SetPublicationOverride — реализовано | feed_id, publication_id, field_id, value, expected_feed_version, expected_version | SetPublicationOverrideResultDTO: publication_version |
| ResetPublicationOverride — реализовано | feed_id, publication_id, field_id, expected_feed_version, expected_version | ResetPublicationOverrideResultDTO: publication_version |
| ChangePublicationStatus | publication_id, status, expected_version | ChangePublicationStatusResultDTO: status, version |
| RefreshPublicationProjection | publication_id | None |
| RequestFeedRefresh | feed_id, expected_version = Feed.version | RequestFeedRefreshResultDTO с текущим состоянием задачи |
| ExecuteFeedRefresh | feed_id, job_id из текущего scheduled_job | None, обновляет FeedExportState |
| RotateFeedPublicLink | feed_id, expected_version = Feed.version | RotateFeedPublicLinkResultDTO с новым адресом |

Редактирование формулы, условий и порядка правил сохраняет актуальную FeedSchema.
При массовом обновлении поля и правила
сохраняют field_id/rule_id; ID новой копии не переиспользуется.

### **6.3. Queries и вычислительный preview**

| Query | Вход | Результат |
| --- | --- | --- |
| ListFeeds | search/status/limit/offset | ListFeedsResultDTO: items/total/limit/offset |
| GetFeed | feed_id | FeedDetailsDTO |
| GetFeedSchema — реализовано | feed_id, текущая рабочая схема | FeedSchemaDetailsDTO: feed_id, version, status, definition |
| ListFieldTypes / ListSourcePaths / ListTransforms | контекст/тип | Собственные DTO метаданных |
| ListCalculationParameters / ListCalculationOperations | контекст/тип | Собственные DTO типов/операций/прав |
| ListFeedPublications | feed_id, фильтры/пагинация | Page[FeedPublicationListItemDTO] |
| GetFeedPublication | publication_id | FeedPublicationDetailsDTO |
| GetPublicationFields — реализовано | feed_id, publication_id | GetPublicationFieldsResultDTO |
| PreviewFeed — реализовано | feed_id, expected_version, серверный лимит 20 | PreviewFeedResultDTO |
| DownloadTestCsv — реализовано | feed_id, expected_version | DownloadTestCsvResultDTO |
| PreviewFieldCalculation | feed_id, catalog_item_id, catalog_variant_id или null, field_id, expected_version, optional definition_override | FieldCalculationPreviewDTO |
| GetFeedExportState | feed_id | FeedExportStateDTO с состоянием задачи, последним отчётом и текущей ссылкой |
| ListLatestFeedExportIssues | feed_id, фильтры и пагинация | Page[FeedExportIssueDTO] последнего отчёта |
| DownloadPublicFeed | public_link_id, format и доверенный tenant из хоста | ArtifactDownloadDTO для streaming из Files |

List/detail Queries читают проекции. Preview исполняет тот же Domain evaluator
на собранных snapshots без изменения бизнес-состояния. definition_override
позволяет проверить структурно корректное несохранённое определение поля,
проходит те же права, валидацию и лимиты. `as_of` задаёт сервер.

### **6.4. UoW, фоновые задачи и события**

Depends открывает UoW и собирает репозитории и адаптер постановки на одной сессии.
Handler получает порты, вызывает Domain и сохраняет результат. Commit выполняется
снаружи до HTTP-ответа, исключение откатывает процесс. Application не присваивает
поля агрегата, не открывает новый UoW и не получает AsyncSession.

RequestFeedRefresh проверяет `Feed.version`, сохраняет текущую задачу со
снимком в `FeedExportState` и ставит её в `scheduled_jobs` в общей транзакции.

Общий `jobs worker` захватывает и продлевает задачу. Адаптер Feed Builder
собирает `ExecuteFeedRefresh` с собственными tenant UoW. Расчёт и
сериализация идут между короткими транзакциями. Files регистрирует файл,
а финальная транзакция проверяет актуальность задачи и `ready` файла перед
сменой ссылки и записью отчёта. Outbox применяется при появлении отдельного
потребителя интеграционного события.

### **6.5. Версии и конкурентные изменения**

row_version используется для Feed и публикации. Для ORM возможен version_id_col,
массовые UPDATE/DELETE явно проверяют expected version и число строк.
Конфликт — VERSION_CONFLICT / 409, не перезапись последним запросом.

`Feed.version` отражает изменения сохранённого Feed. Версия формата JSON задаётся
`schema_format_version`, версия вычислителя — `calculation_engine_version`.
Повтор задачи идемпотентен. Совпадение `job_id` и владение текущей арендой
`scheduled_jobs` обязательны для записи результата.
Ревизии источников и временная актуальность проверяются независимо от row_version.

## **7. Value Resolution Engine и параметры товара**

### **7.1. Источники и зарегистрированные параметры**

| Provider / path или parameter ID | Тип и смысл |
| --- | --- |
| catalog / item.title | Локализованный STRING |
| catalog / item.description | Локализованный TEXT |
| catalog / item.sku | Языконезависимый STRING |
| catalog / item.regular_price | Денежный источник без наценки |
| catalog / item.stock_quantity | Эффективный целочисленный остаток либо отсутствие при выключенном учёте |
| catalog / item.in_stock | BOOLEAN, `true` для `in_stock`, `false` для `out_of_stock` и `on_backorder` |
| price.regular | Точная числовая сумма обычной продажной цены |
| price.sale | Действующая акционная цена на as_of, либо отсутствие |
| price.effective | Sale при действующей акции, иначе regular |
| price.purchase | Собственная закупочная цена `purchase_price` выбранного SIMPLE или VARIANT из Catalog либо отсутствие значения |
| stock.quantity / stock.in_stock | Остаток и наличие в условиях, варианты наследуют складские данные по правилам Catalog |
| product.category_ids | Набор явно назначенных UUID категорий |
| product.sku / product.id | SKU / идентификатор товара |

Все price.* передают точные Decimal без валютной размерности. Валютную метку
результата задаёт определение MONEY-поля.

Прямые источники Catalog соответствуют SourceProvider.CATALOG и
CatalogSourcePath. Коды price.*, stock.* и product.* в таблице — отдельные параметры AST,
а не дополнительные значения CatalogSourcePath. ParameterReferenceVO проверяет форму
ID; реализованная PriceCalculationSemanticPolicy проверяет закрытый реестр и типы
всех ветвей до чтения товаров. Метаданные API содержат параметры из таблицы.
Catalog хранит обычную, акционную и закупочную цены позиции, а также UTC-интервал
акции. Пакетный снимок передаёт закупочную цену и категории выбранной позиции.

Каждый параметр имеет стабильный ID, тип, cardinality/nullability, разрешённые
операции и правила доступа. price.sale вне интервала акции отсутствует, хотя
в исходной спецификации может храниться запланированная sale price.
Если позднее понадобится необработанная плановая цена, вводится отдельный parameter ID.

Расширение реестра не требует нового поля SQL на каждую характеристику.
Параметры не обращаются к результатам других вычисляемых полей Feed в MVP.

### **7.2. Пакетные снимки Catalog**

CatalogProductReader получает пары catalog_item_id/catalog_variant_id и набор
целевых/fallback locales. Он возвращает immutable snapshots выбранных продаваемых
позиций, их роли/ID, принадлежности родителю, эффективного контента, обычной,
акционной и закупочной цен, интервалов акций, категорий и ревизий. Для SIMPLE
субъект — сам товар. Для VARIANT субъект — выбранный вариант, catalog_item_id
остаётся ссылкой на его родителя.

TITLE/DESCRIPTION разрешаются для выбранной позиции по правилам наследования
Catalog отдельно для каждой запрошенной locale; языковой fallback Feed применяется
по своей явной политике. SKU и regular/sale/purchase price принадлежат самой продаваемой
позиции. У VARIABLE цены нет, подмена цены варианта ценой родителя не допускается.
product.id и product.sku относятся к выбранному SIMPLE/VARIANT; категории и другие
наследуемые параметры определяются публичным контрактом владельца данных.
Новые произвольные пути в SourceReferenceVO для этого не вводятся.

FeedBuilder не импортирует внутреннюю Policy наследования Catalog и не дублирует
её. Порт/адаптер получает эффективные значения через публичную границу владельца;
если нужного чтения вариантов ещё нет, сначала согласуется минимальный owner-контракт.
Родитель читается только как контекст, его остальные варианты не становятся
участниками Feed. В source revisions учитываются выбранная позиция и родитель,
если его данные использованы; их изменения делают зависимую проекцию STALE.
Денежные исходные значения сохраняют точность Decimal до вычисления. Описание —
plain text; HTML предоставляется отдельной безопасной проекцией/явным transform.

`price.purchase` получает `purchase_price` выбранной позиции из того же снимка.
`null` означает отсутствие значения, `0` — корректную закупочную цену. Зависимость
от этой цены привязана к ревизии выбранной позиции, в том числе когда условие
проверило отсутствие цены. Добавление, изменение или очистка закупочной цены
в Catalog делает зависимую проекцию STALE.

Потребности собираются из definition до пакетного чтения. Отсутствие параметра
в неисполненной ветви не становится блокирующим issue. Если выбранное выражение
требует отсутствующую закупочную цену, возвращается CALCULATION_PARAMETER_MISSING.

### **7.3. Контекст разрешения**

ResolutionContext содержит tenant/feed/publication IDs, catalog_item_id,
catalog_variant_id или null, ID выбранной продаваемой позиции, as_of и
calculation_engine_version. Предпросмотр использует версию прочитанного Feed,
а пересборка — job_id и снимок текущей задачи. Локаль берётся из
StringFieldTypeVO/TextFieldTypeVO, необязательная
валютная метка — только из MoneyFieldTypeVO. Валюта источника не определяет результат.
ID выбранной позиции выводится из пары: catalog_variant_id, если он задан,
иначе catalog_item_id; отдельной изменяемой настройки выбранного ID нет.
Тип определяется классом type_definition/kind без отдельного поля value_type.
Один context используется preview/resolve/serializer без скрытого чтения часов.

ResolvedField: field_id/key/type, source_value при необходимости, override_value,
resolved_value, origin=INHERITED / CALCULATED / MANUAL, issues, actual_locale,
валюта, использованные source revisions и безопасный calculation trace.
Fallback отмечается явно в actual_locale/метаданных, не отдельным скрытым источником.

### **7.4. Последовательность FieldValueResolver**

1. Если есть override — взять ручное значение; автоматическое определение
   не исполняется. Иначе перейти к type_definition.value_definition.
2. MANUAL без override — отсутствующее значение. SOURCE — получить источник.
   Для MONEY используется точная сумма; валюта источника не наследуется.
3. CALCULATED — собрать числовые параметры, выбрать правило/ELSE и вызвать
   чистый evaluator. Пользовательский курс вычисляется как обычная арифметика.
4. Проверить тип, применить type_definition.transforms в порядке схемы,
   затем числовой контракт и type_definition.constraints без Shared MoneyVO.
5. Для MONEY сформировать PriceValueVO(amount, currency), где currency
   взята только из определения поля. None остаётся отсутствием метки.
6. Вернуть значение/origin/trace/issues; PublicationResolver собирает readiness.

Manual MONEY содержит PriceAmountVO без своей валюты. Формула/наценка источника
не применяются повторно; transforms и constraints продолжают действовать.
Для диагностического сравнения preview может отдельно читать источник;
сбой необязательного чтения не делает корректный override ошибочным.

### **7.5. Локализация и отсутствующие значения**

NONE не подставляет другой язык; LOCALE_CHAIN проверяет явно заданную цепочку.
MANUAL_REQUIRED требует ручного перевода при отсутствии целевого. Обязательная
пустая строка после trim — REQUIRED_VALUE_MISSING. Необязательный отсутствующий
перевод с NONE допустим. Null, пустая строка, отсутствие override и reset различаются.

Ошибки расчёта выбранного денежного источника/ветви — INVALID, даже если поле
не required. Техническая недоступность — SOURCE_UNAVAILABLE/DEPENDENCY_UNAVAILABLE,
а не обычное отсутствие. Ошибки в неподходящих ветвях не исполняются и не мешают
готовности. Перед созданием задания определение проверяется целиком, включая
неисполняемые ветви.

### **7.6. Чистые handlers и округление**

StringFieldHandler, TextFieldHandler, MoneyFieldHandler проверяют значения;
TransformRegistry выбирает зарегистрированные чистые handlers. NaN/Infinity,
float и несовместимые типы не допускаются. Списки возможностей выдаёт backend.

Для ceil_step: units=ceil(amount/step), result=units*step, step>0. Валюта сохраняется.
590.21 при step=0.1 даёт 590.3; представление 590.30 допустимо без потери значащих
разрядов. Serializer не округляет скрыто до двух знаков. Формат/финальное округление
должны учитывать числовой контракт FeedBuilder; валютная метка не задаёт точность.

### **7.7. PublicationResolver и актуальность**

Snapshot товара и параметры читаются пакетно для всех нужных полей/локалей.
Идентичные зависимости можно кешировать в рамках контекста; key включает tenant,
пару item/variant IDs, фактические source revisions, определение, валютную метку и as_of.
Кеши соседних вариантов не смешиваются; родительская revision учитывается при
наследовании. Разные поля могут иметь разные
формулы; общей наценки Feed поверх результата не существует.

Проекция хранит версии Feed и публикации, source revisions, as_of,
valid_until. При условном upsert старый worker не перезаписывает новый.
Текущий список читает проекции, preview и экспорт вычисляют результат заново.
Зависимости override и неприменённых ветвей не включаются как нужные для результата.
Сведения для EXISTS/IS_MISSING и проверенных условий также являются зависимостями:
появление ранее отсутствовавшего значения должно инвалидировать проекцию.

## **8. Условия и формулы денежного поля**

### **8.1. Область действия и способы получения значения**

Правила принадлежат конкретному MONEY-полю сохранённой FeedSchema.
Они не записываются в Catalog и не назначаются другим Feed автоматически.
Несколько денежных полей могут независимо рассчитывать розничную/партнёрскую/
акционную цену и цену в другой валюте. Ключ поля не влияет на семантику.

MoneyValueDefinitionVO имеет режим SOURCE, MANUAL или CALCULATED. Последний
содержит PriceCalculationVO с rules и default_expression. Выражение
`price.purchase` возвращает исходную закупочную цену Catalog. Процентная или
фиксированная надбавка в UI помогает построить выражение конечной цены.
PriceAmountVO содержит только сумму. Необязательная currency принадлежит полю;
PriceValueVO объединяет сумму и выбранную метку при разрешении значения.

### **8.2. Выбор IF / ELSE IF / ELSE**

```text
IF product.category_ids CONTAINS category_uuid AND price.purchase EXISTS
    THEN price.purchase × 1.25
ELSE IF price.sale EXISTS
    THEN price.sale × 1.10
ELSE
    price.regular × 1.15
```

Правила проверяются последовательно. Первое истинное условие выбирает единственное
выражение; остальные правила не исполняются. Если совпадений нет — обязательный
ELSE/default_expression. Пустой список rules допустим. Эффекты/наценки правил
не суммируются и не применяются каскадом. Порядок входит в определение схемы.

ALL/ANY используют короткое замыкание слева направо, NOT имеет один операнд.
Вычисляется только выбранная формула. Ошибка условия не превращается в False;
для отсутствующих данных служат EXISTS/IS_MISSING. Ошибка выбранной формулы
не приводит к скрытому переходу на следующую ветвь или ELSE.

### **8.3. Условия и типы параметров**

| Оператор | Семантика |
| --- | --- |
| EQ / NE | Равенство/неравенство совместимых типов |
| GT / GTE / LT / LTE | Упорядоченное сравнение числовых сумм и других Decimal-параметров |
| IN / NOT_IN | Скаляр принадлежит явно заданной однородной коллекции |
| CONTAINS | Коллекция слева содержит скаляр справа |
| EXISTS / IS_MISSING | Явная проверка наличия, 0/False/пустая коллекция не равны отсутствию |
| ALL / ANY / NOT | Логическое объединение |

Категория сравнивается по UUID, а не по переведённому названию. Список включает
явно назначенные категории; предки не добавляются. Условие по поддереву потребует
отдельной зарегистрированной операции и snapshot дерева от владельца, после MVP.
Дополнительные параметры Catalog, например бренд и характеристики, подключаются
через ParameterRegistry с явным типом и источником.

### **8.4. Арифметика и конечный результат**

| Задача | Выражение |
| --- | --- |
| +20% к обычной цене | price.regular × 1.20 |
| +30% к закупочной | price.purchase × 1.30 |
| Фиксированная надбавка | price.regular + 50 |
| −5% от акционной | price.sale × 0.95 |
| Цена не ниже закупки с наценкой | max(price.sale, price.purchase × 1.15) |
| Маржа 25% от закупки | price.purchase / (1 − 0.25) |

Все формулы возвращают конечный числовой Decimal суммы MONEY-поля.
MAX не подменяет отсутствующую sale price: нужен EXISTS или явная ветвь ELSE.
UI «+20%» строит AST price × (1 + 20 / 100), без вычисления коэффициента через float. Пересчёт пользователь задаёт явно:
price.regular / 40 для деления на курс или price.regular * 1.20 / 40
для пересчёта с наценкой. CurrencyVO("USD") сам по себе сумму не изменяет.

Допустимы ADD/SUBTRACT/MULTIPLY/DIVIDE, унарный NEGATE и MIN/MAX/ABS над числами.
Все цены и числовые константы участвуют как Decimal; отдельной валютной
размерности и денежных литералов нет. Параметры категории/UUID/строки/boolean
применяются только в подходящих условиях, не подменяют числовые операнды.

AST содержит ParameterReferenceVO, DecimalLiteralVO, ArithmeticExpressionVO,
FunctionExpressionVO; ScalarLiteralVO нужен для UUID/строк/boolean,
CollectionLiteralVO — для однородных tuples литералов условий.
В JSON Decimal — строка; boolean и UUID проверяются явно. Каждый вид узла
имеет конкретный контракт/арность; неизвестные свойства/операции отклоняются.
Пользовательские функции, внешний код и ссылки на вычисляемые поля не входят в MVP.
MoneyLiteralVO удалён; schema_format_version остаётся 1 до выпуска persistence/API,
совместимые aliases прежнего денежного AST не вводятся.

Канонические свойства узлов:

| kind | Свойства |
| --- | --- |
| parameter | parameter: зарегистрированный ID |
| decimal | value: конечная десятичная строка |
| scalar | value_type: uuid/string/boolean, value соответствующего типа |
| collection | item_type и items одного скалярного типа |
| arithmetic | operator и left/right; для NEGATE только operand |
| function | function: MIN/MAX/ABS, arguments: массив выражений |
| comparison | operator, left, right |
| logical | operator и operands; NOT имеет ровно один |
| presence | operator: EXISTS/IS_MISSING и parameter |

MIN/MAX принимают минимум два аргумента, ABS — один. Неупомянутые альтернативные
свойства узла отсутствуют, а не игнорируются. Группы ALL/ANY непустые.

### **8.5. Валютная метка, точность и время**

Один as_of определяет действие всех акций. Арифметика использует числовые суммы
источников без автоматического пересчёта или наследования валюты.
Курс/коэффициент находится в пользовательской формуле и фиксируется её снимком.
currency: CurrencyVO | None = None задаёт только код результата, например USD.
Смена метки не меняет сумму, не требует нового field_id и инвалидирует
конфигурацию результата как изменение настроек поля.

Рабочий Decimal context фиксируется версией evaluator (начально precision=40,
ROUND_HALF_UP для деления), не зависит от настроек процесса. На входе/каждом узле
нет квантования до 4 знаков. Результат должен соответствовать числовому бюджету;
округление с шагом задаётся явным MONEY_CEIL_STEP. Нет округления по коду валюты.
Недопустимый результат возвращает issue, а не скрытое обнуление.
Отрицательность проверяет min_amount поля, а не название price.

PriceAmountVO — сумма override без валюты. PriceValueVO — разрешённый
результат с amount и необязательной currency из поля; валютная метка не дублируется
в override. Ни один из этих объектов не выполняет конвертацию.
Деление на ноль/отсутствующий параметр обрабатываются как ошибки выбранной ветви;
неисполненные ветви не создают зависимостей или курсовых запросов.

### **8.6. Ошибки и объяснимость**

Нет цены/параметра — не ноль. Сравнение с отсутствующим значением даёт ошибку,
кроме явных проверок наличия. 0 и False валидны. Рекомендуемый шаблон:
IF price.purchase EXISTS → price.purchase × 1.25, ELSE price.regular × 1.10.

| Код | Причина |
| --- | --- |
| CALCULATION_PARAMETER_MISSING | Нужный выбранной ветви/условию параметр отсутствует |
| INVALID_EXPRESSION_TYPE | Несовместимая операция или конечный тип |
| DIVISION_BY_ZERO | Нулевой делитель |
| NUMERIC_RANGE_EXCEEDED | Недопустимый диапазон/результат |
| CALCULATION_LIMIT_EXCEEDED | Превышен лимит исполнения |
| UNSUPPORTED_CALCULATION_VERSION | Не поддерживается семантика/формат дерева |

Issue содержит field_id, optional rule_id и path узла. Trace: выбранное правило
либо ELSE, проверенные условия, реально использованные параметры/ревизии,
числовые операции, округление и конечный результат. Исходная закупочная цена и
производные промежуточные суммы показываются только при соответствующих правах.

### **8.7. Ответственность слоёв и будущая редактура**

Domain содержит определения и, в более позднем срезе, чистые ConditionEvaluator,
ExpressionEvaluator и MoneyFieldCalculator. Они не получают repositories/HTTP.
Application строит snapshots и вызывает Domain; Infrastructure читает источники,
курсы и хранит файлы; UI строит AST и показывает серверное объяснение.

Изменение правила сохраняется через корень Feed и применяется при следующем
запуске. Активный файл меняется после успешной активации новой генерации.
Копирование поля/правила создаёт новые ID. Редактирование внутри того же поля
сохраняет field_id/rule_id. Порядок правил и формулы входят в снимок генерации.

## **9. Управление публикациями и расчётным preview**

### **9.1. Привязка товаров**

AddCatalogItemsToFeed принимает явный список item_references. Каждый элемент
содержит catalog_item_id и catalog_variant_id (null для SIMPLE, ID варианта для
VARIANT). Одного списка ID родителей недостаточно: запрос должен однозначно
обозначать выбранные продаваемые позиции.

Пользователь может добавить простой товар, конкретный вариант или выбрать
несколько вариантов внутри VARIABLE. Действие «Добавить все существующие варианты»
получает текущий список через публичное чтение Catalog и фиксирует конкретные
пары ID перед отправкой mutation; backend повторно проверяет тип/существование,
принадлежность, доступ и допустимость по контракту Catalog. VARIABLE с null вместо
варианта отклоняется, а не раскрывается автоматически в момент генерации.

Текущий AddCatalogItems использует сохранённый Feed, включая фид с пустой схемой.
Application проверяет права, получает Feed и внешние факты
о выбранных ссылках через CatalogProductReader. Domain получает типизированные
данные для проверки собственных правил публикации, без I/O; допустимость
product_mode проверяет VO настроек. В одной транзакции создаются недостающие
FeedPublication; постоянные задачи проекций появятся отдельно. Результат отображает каждую нормализованную
пару ID в publication_id. Неверная ссылка отклоняет запрос без частичной привязки.
Повторная/конкурентная привязка, включая пересечение одиночного выбора и «добавить
все», не создаёт дубль и не стирает существующие overrides/status.
NULLS NOT DISTINCT защищает identity простой позиции с catalog_variant_id=None;
ненулевой ID варианта различает публикации одного родителя.

Текущий набор фиксируется публикациями. Новые варианты Catalog не подключаются
автоматически; повтор mutation использует тот же явный список ссылок. Динамические
правила ассортимента остаются отдельным расширением. Для топика с чёрным,
коричневым и белым вариантами выбор только белого создаёт одну публикацию:

```json
{
  "item_references": [
    {
      "catalog_item_id": "20000000-0000-4000-8000-000000000001",
      "catalog_variant_id": "20000000-0000-4000-8000-000000000004"
    }
  ]
}
```

Имена/цвета помогают выбору в UI; идентичность задаётся ID. Родитель и два других
варианта не получают публикации и экспортные записи. Если выбранные связи
Catalog позднее удалены, несовместимо изменены или позиция недоступна, readiness
показывает проблему; скрытой замены другой вариацией, родителем или автоматического
выбора всех вариантов нет.

Категории и цены могут отсутствовать; это не препятствует самой привязке товара.
Они проверяются только в тех определениях/условиях, которым нужны при resolve.
Внешняя техническая недоступность не маскируется отсутствием товара.

Текущий запрос содержит expected_feed_version и от 1 до 100 item_references.
Сначала проверяется полный пакет: неверная ссылка отклоняет его до записи.
Нормализация сохраняет порядок первых вхождений. Ответ для каждой ссылки содержит
id, пару Catalog ID, status/version и outcome CREATED/EXISTING, плюс feed_version.
Повтор не возобновляет PAUSED и не возвращает ARCHIVED автоматически.
Пустая схема, отсутствующие цена/перевод допускают добавление; архивные/удалённые
позиции Catalog и неверные пары отклоняются. Удаление источника впоследствии
сохраняет публикацию, список показывает source_available=false.

### **9.2. Установка и сброс override**

SetPublicationOverride проверяет версии Feed и публикации, field_id сохранённой
схемы, тип и ограничения значения. Ошибочный ввод остаётся в редакторе.
Валидный override сохраняется в агрегате публикации в общей транзакции.
Сумма передаётся Decimal-строкой и создаёт PriceAmountVO; валюту override
не принимает. Максимальная длина текста проверяется на вводе и после
преобразований. Нарушение правил поля возвращает 422 с указанием field_id.
Ручная цена не проходит формулу/наценку источника, но transforms и constraints
проверяются. Currency результата берётся только из определения поля.

Reset удаляет запись override отдельным действием с версиями Feed и публикации.
После сброса снова применяется type_definition.value_definition поля.
Ручной null — не reset.
Старые overrides удалённого поля сохраняются. При расчёте рассматриваются поля
сохранённой схемы. Поле с новым смыслом получает новый field_id.

### **9.3. Preview**

GetPublicationFields использует сохранённую схему и возвращает исходные и
итоговые значения полей позиции, ручной ввод и диагностику. Реализованный
PreviewFeed обрабатывает до 20 ENABLED-публикаций, а
DownloadTestCsv обрабатывает весь ENABLED-ассортимент. Оба сценария используют
один PublicationResolver и сохранённые определения Feed. Пустая схема и пустой
ассортимент отображаются в Console отдельными состояниями.
PreviewFieldCalculation проверяет выбранную пару catalog_item_id/catalog_variant_id
и конкретное денежное поле, включая optional несохранённое определение после
структурной проверки. Для варианта preview использует тот же эффективный контекст,
что публикация и экспорт; ID родителя не подменяет выбранную позицию.

Предпросмотр работает на чтение. Общие as_of и снимки определений обеспечивают
согласованность одного запроса. Повторный preview может взять новое время и
исходные ревизии. Trace фильтруется правами; режим тестирования не
позволяет обойти закрытые закупочные данные или проверить произвольный код.

### **9.4. Проекции и участие**

Refresh получает snapshots, выполняет resolve и условно записывает проекцию при
актуальных версиях Feed, публикации и задачи расчёта. Результат старого worker
отбрасывается. После сохранения схемы или настроек несовпадение версий определяет
STALE при чтении.

valid_until проверяется при чтении/следующем resolve; граница акции делает кеш
устаревшим без события изменения. Это не равно автоматической генерации по расписанию:
активный файл меняется только новым Generation Request. Списки показывают дату
расчёта/устаревание и не обещают цену реального времени в уже выпущенном артефакте.

В экспорт входят только ENABLED. Изменение участия/удаление привязки проходит
через Domain публикации и не меняет Catalog. Исторические issues сохраняют
безопасные сведения даже после удаления текущей публикации.

## **10. Генерация CSV/XML**

### **10.1. Внутренняя экспортная модель**

Сериализатор записывает упорядоченные типизированные значения по экспортным
именам полей. Формулы и чтение Catalog выполняются до сериализации.

```python
@dataclass(frozen=True)
class ExportCell:
    """Передаёт одно проверенное значение для сериализации."""

    field_id: UUID
    export_name: str
    value_type: FieldValueType
    value: DomainValue | None


@dataclass(frozen=True)
class ExportRecord:
    """Передаёт упорядоченные ячейки публикации выбранному сериализатору."""

    publication_id: UUID
    cells: tuple[ExportCell, ...]
```

Порядок `cells` совпадает с порядком полей FeedSchema.
При VARIABLE_TO_SINGLE каждая участвующая публикация SIMPLE/VARIANT после проверки
готовности даёт ровно одну ExportRecord и одну CSV-строку/XML-элемент. ID публикации
стабилен между генерациями; номер строки и порядок вариантов не определяют identity.
Отдельных записей VARIABLE, вложенных вариантов и групповых связей нет.
Сериализатор не раскрывает родителей и не выбирает ассортимент — он записывает
уже подготовленный плоский поток. В схему не добавляются системные поля Type,
Parent или group_id.

Это позволит добавлять новые поля без изменения сериализаторов CSV/XML.

### **10.2. CSV Serializer**

Контракт сериализатора:

```python
class FeedSerializer(Protocol):
    """Преобразует проверенный поток записей в выбранный экспортный формат."""

    def serialize(
        self,
        *,
        records: AsyncIterator[ExportRecord],
        schema: FeedSchema,
        settings: ExportFormatSettings,
    ) -> AsyncIterator[bytes]:
        """Возвращает байты без изменения значений, бизнес-правил и источников."""
        ...
```

Application берёт один definition_snapshot.export_settings.format_settings, выбирает
сериализатор по фиксированному settings.format и передаёт ему этот VO. CSV получает
CsvExportSettingsVO, XML — XmlExportSettingsVO; неподдержанный тип отклоняется.
В Domain и первом срезе не создаются registry/serializer заготовки.

CsvFeedSerializer создаёт header из schema.exported_fields, затем потоково
записывает значения cells. Он получает delimiter/encoding/include_header из
переданного CsvExportSettingsVO зафиксированного снимка, а не общих csv-настроек Feed.

Правила:

- UTF-8.
- Разделитель `,` по умолчанию.
- Колонки формируются в порядке схемы.
- Строковые значения корректно экранируются при наличии запятых, кавычек и переносов.
- MONEY с currency=None сериализуется как десятичная сумма без валютной метки.
  С заданной меткой Generic CSV добавляет её через пробел: 25.00 USD.
  Само числовое значение и его точность сериализатор не меняет.
- Для значений, которые могут восприниматься электронными таблицами как формулы, предусмотрена отдельная политика безопасности CSV, не искажающая машинный импорт молча.

### **10.3. XML Serializer**

XmlFeedSerializer потоково записывает XML declaration, корневой элемент,
элемент каждой публикации и теги exported cells. root_name/item_name берутся
из переданного XmlExportSettingsVO зафиксированного снимка.
Поля с `export.xml_placement: ATTRIBUTE` записываются в открывающий тег
предложения под именем `export.name`, например `<offer id="123" available="false">`.
Console задаёт это размещение чекбоксом и показывает `@id` в XML-предпросмотре.
В CSV такое поле остаётся обычной колонкой. Отсутствующий необязательный атрибут
пропускается, числа и логические значения сохраняют `0` и `false`.
MONEY записывается десятичной суммой; заданная метка становится атрибутом
currency: <price currency="USD">25.00</price>. При currency=None атрибут отсутствует:
<price>25.00</price>. Это представление значения, не дополнительное поле схемы.
Для MONEY-поля с размещением `ATTRIBUTE` значение атрибута содержит только сумму,
например `<offer price="25.00">`.
Для отсутствующего необязательного значения
Generic CSV записывает пустую ячейку, Generic XML опускает элемент; профиль
может явно задать другое представление, не меняя FieldValueResolver.

`write_element()` должен экранировать спецсимволы XML и отклонять недопустимые
символы XML 1.0. Имена тегов проверяются на сохранённой схеме и настройках при
запросе генерации.

### **10.4. Пример результата**

Пример произвольной пользовательской схемы; перечисленные поля не создаются автоматически:

```csv
title_uk,title_ru,description_uk,price_uah,price_usd
"Хлорофіл NOW Foods","Хлорофилл NOW Foods","Рідкий хлорофіл",1200.00 UAH,30.00 USD
```

```xml
<?xml version="1.0" encoding="UTF-8"?>
<catalog>
  <product>
    <title_uk>Хлорофіл NOW Foods</title_uk>
    <title_ru>Хлорофилл NOW Foods</title_ru>
    <description_uk>Рідкий хлорофіл</description_uk>
    <price_uah currency="UAH">1200.00</price_uah>
    <price_usd currency="USD">30.00</price_usd>
  </product>
</catalog>
```

Это альтернативные представления одной схемы: конкретный Feed создаёт только
CSV либо XML согласно format_settings. Оба примера не означают два файла одной
генерации; для обоих нужны отдельные Feed. В примере обоим MONEY-полям заданы
валютные метки. Если currency=None, CSV передаёт только сумму, XML — сумму без
атрибута currency. Метка не зависит от имени price_uah/price_usd и не выполняет
пересчёт. Сериализаторы и PriceValueVO будут реализованы в следующих срезах.

### **10.5. FeedSchema и FormatProfile**

```text
FeedSchema → ResolvedPublication → FormatProfile → Serializer
                                    ├── Generic CSV
                                    ├── Generic XML
                                    ├── Prom YML (после MVP)
                                    └── Rozetka XML (после MVP)
```

FeedSchema определяет пользовательские значения, FormatProfile — контракт
целевого формата: соответствие экспортных полей/имён, допустимые валюты,
обязательные поля и структуру. Общая внутренняя схема не означает, что любой
маркетплейс примет произвольные title_uk/price_usd. Профили площадок реализуются
отдельно по их официальным спецификациям, актуальным на момент реализации.

Generic CSV/XML дают свободные имена и порядок в пределах безопасной валидации.
Профиль не пересчитывает цены и не смешивает языки. Исходные значения поступают
через порты владельцев данных, коммерческие выражения исполняет вычислитель
денежного поля FeedBuilder. Новые профили не требуют копировать публикации или
создавать отдельную версию товара Catalog. VARIABLE_TO_SINGLE описывает плоское
представление продаваемых позиций, но не является профилем Prom/WooCommerce и
не гарантирует готовность их обязательных колонок. Группировка/родительские строки
появятся через новые явно поддержанные режимы и профильные правила после MVP.

### **10.5.1. Поле категории в конструкторе схемы**

Тип `category` хранится в `root.fields[]` и использует обычное сохранение схемы.
`type_definition.object_schema` описывает свойства записи, ключи ID и названия
и их XML-размещение. `type_definition.value` хранит записи, родителей и
упорядоченные правила выбора. У каждого поля свой набор записей и собственные ID.

`export.document` задаёт контейнер, имя записи, место вывода и форму вложенности.
`export.publication` выбирает свойство, которое экспортируется в предложение
через обычное имя и XML-размещение поля. Можно включить один из выходов или оба.
Если настроены оба выхода, дерево включает записи выгруженных предложений и их
предков. Если настроено только дерево, выводятся все записи поля. В CSV поля
категорий пропускаются.

Сериализатор получает готовые XML-узлы. Атрибуты площадок, включая `portal_id`
и `rz_id`, описываются свойствами записи. Старый корневой `categories` читается
через совместимость со старыми документами и задачами. Сохранение записывает
только поля. Таблицы базы данных для этой структуры не нужны.

### **10.6. Точность и профиль формата**

Serializer не выполняет арифметику, дополнительную наценку и скрытое округление.
Количество знаков следует явным настройкам/разрешённой точности. Формат с двумя
знаками применяется только после соответствующего полевого округления либо
если значащие разряды не теряются. Все вычисленные числа сериализуются десятично.
Поле constraints.required — пользовательское, требования площадки — профильные.
Пресет только заполняет исходную схему, не заменяет FormatProfile-валидацию.

## **11. Фоновое обновление файла и публичная выдача**

### **11.1. Полный процесс**

```text
RequestFeedRefresh → FeedExportState.PENDING + снимок настроек + scheduled_job
  → jobs worker → ExecuteFeedRefresh → RUNNING + as_of
  → ENABLED-публикации пакетами → Catalog → PublicationResolver
  → счётчики и диагностики текущей проверки
  → STRICT допускает публикацию при отсутствии блокирующих ошибок
  → один CSV в Files → обновление active_file_id и последнего отчёта
  → GET на хосте tenant → Feed Builder → поток из Files
```

При отклонении обновляется отчёт. По существующей ссылке продолжает
выдаваться прежний файл.

### **11.2. Запрос и фиксированный контекст**

`RequestFeedRefresh` проверяет права, `Feed.version`, состояние Feed, наличие
экспортируемых полей и пригодность сохранённой конфигурации. Для CSV и XML
воркер использует формат и политику проверки из сохранённого снимка задачи.

Под блокировкой Feed и его `FeedExportState` создать одну текущую задачу
`feed_builder.generation.run` через существующий `ScheduleScheduledJobUseCase`.
Запись состояния и задачи выполняется в одной транзакции. Задача содержит
`tenant_id`, `job_id`, `run_at = now` и `feed_id` в payload. Повторное нажатие
возвращает состояние незавершённой задачи. После её завершения следующая
пересборка получает новый `job_id`.

Первый запуск фиксирует `as_of` до чтения данных. Повтор сохраняет то же
`as_of`, схему, параметры формата, пользовательские константы формул и версию
движка. Catalog и включённые публикации читаются при выполнении пакетами;
их данные могут измениться между попытками. Работа с очередью, heartbeat,
лимит попыток и восстановление относятся к общему `jobs worker`.

### **11.3. Выполнение и отчёт**

Выбранные ENABLED-публикации SIMPLE/VARIANT обрабатываются в стабильном
keyset-порядке. Application читает необходимые поля Catalog через публичный
контракт и передаёт снимки в существующий `PublicationResolver`. Каждое поле
использует своё определение. При ручном значении исходная формула не нужна.
Сериализатор получает проверенные записи и параметры формата из снимка.

Каждая позиция учитывается один раз. Блокирующая ошибка относит её к
`rejected_items`, допустимое предупреждение — к `warning_items`, остальные
позиции — к `valid_items`. Предупреждения допускаются в файле. Коды
предупреждений определяются политикой явно. Для отчёта по данным проход
продолжается после первых ошибок. Технический сбой может дать неполный отчёт
после исчерпания повторов. Счётчики описывают проверку, а факт публикации
отражается итогом `PUBLISHED`, `REJECTED` или `FAILED`.

При `STRICT` блокирующая ошибка даёт `REJECTED` и сохраняет активный файл.
В `SKIP_INVALID` из примера 90 успешных, 5 с предупреждениями и 5 отклонённых
получится файл с 95 записями. Если все выбранные позиции отклонены или
возник технический сбой, прежняя выдача сохраняется в обоих режимах.

### **11.4. Замена файла, повторы и согласованность**

Расчёт и подготовка CSV ведутся вне длительной SQL-транзакции. Готовый
поток или временный файл передаётся в Files с точным размером, именем и MIME.
При фиксации проверяются текущий `job_id` и право worker завершить задачу
через `owns_current_lease(..., for_update=True)`. Под блокировкой Feed и
состояния проверяются статус Feed и совпадение сохранённых схемы и настроек
со снимком. Готовность `StoredFile` проверяется под Files lock в том же tenant UoW.

При принятии результата регистрация `StoredFile`, смена `active_file_id`
и запись фактического формата, дат выдачи и отчёта фиксируются одной транзакцией.
Первая публикация также
переводит Feed из DRAFT в ACTIVE и создаёт `public_link_id`. Ротация ссылки
проверяется независимо от снимка расчёта. При изменении схемы или настроек
во время сборки итог `REJECTED` сохраняет причину и прежний файл.
Повтор, пришедший после уже зафиксированного результата, не заменяет его.

После commit отложенная задача очищает прежний файл по правилам Files.
До переключения новый файл может существовать временно. Публичный маршрут
разрешает только активный file_id. После падения worker повторы выполняет
scheduler. Сверка переводит незавершённое состояние в `FAILED` после
исчерпания попыток. Временные файлы и staging очищаются с проверкой ссылки
и актуальной задачи.

### **11.5. Публичный HTTP-маршрут**

```text
https://<tenant-host>/api/public/feed-builder/<public_link_id>/feed.csv
https://<tenant-host>/api/public/feed-builder/<public_link_id>/feed.xml
```

Маршруты CSV и XML используют существующее проксирование `/api/` и tenant
admission по доверенному хосту. При отсутствии
доверенного tenant запрос завершается до чтения данных Feed. Публичный GET
ищет `public_link_id` только в схеме текущего tenant, проверяет доступность
Feed и фактический формат активного файла. Отсутствующий файл, старый адрес,
архивный Feed и несовпадение расширения дают 404. Ссылка для Console строится
из доверенного домена tenant.

`PUBLIC` работает без cookie и токена. Публичный ID используется для поиска
текущего адреса. Feed Builder получает поток через `GetFileContentHandler`
и отдаёт CSV как `text/csv` с `Content-Disposition: attachment`. XML отдаётся
как `application/xml` с `Content-Disposition: inline`. HTTP UoW закрывается
до передачи потока. Tenant admission удерживается до закрытия потока.

Обычная пересборка сохраняет адрес при прежнем формате. Команда замены
ссылки меняет `public_link_id`, старый URL перестаёт работать. ETag и
Last-Modified относятся к активному файлу. Кеш перепроверяет адрес перед
повторной выдачей. Проверка маршрута выполняется до условного ответа 304.
Будущий `PRIVATE` потребует `?token=…` по разделу 16.8.

## **12. Presentation: целевой REST API**

Реализованы Feed CRUD, чтение и сохранение схемы, метаданные, управление
ассортиментом, расчётный предпросмотр и пробный CSV. Обновление файла и публичная ссылка относятся
к срезу 16.7. Приватные ключи относятся к 16.8.
Административный префикс — /api/console/feed-builder.
Controller/request/response каждого метода находятся в отдельных файлах,
router только регистрирует маршруты/статусы/Depends. HTTP DTO не входят в Domain.

### **12.1. Feed, схема и метаданные**

| Метод | Путь после префикса | Сценарий |
| --- | --- | --- |
| POST | /feeds | CreateFeed |
| GET | /feeds | ListFeeds |
| GET | /feeds/{id} | GetFeed |
| PATCH | /feeds/{id} | UpdateFeed |
| DELETE | /feeds/{id}?expected_version=N | ArchiveFeed: 204 без тела |
| GET | /feeds/{id}/schema | GetFeedSchema: сохранённая схема Feed |
| PUT | /feeds/{id}/schema/draft | SaveFeedSchemaDraft: заменить сохранённую схему Feed |
| POST | /feeds/{id}/preview | PreviewFeed: до 20 включённых публикаций |
| POST | /feeds/{id}/test-csv | DownloadTestCsv: пробный файл по всему включённому ассортименту |
| POST | /feeds/{id}/calculation-preview | PreviewFieldCalculation |
| GET | /field-types | ListFieldTypes |
| GET | /source-paths | ListSourcePaths |
| GET | /transforms | ListTransforms |
| GET | /calculation-parameters | ListCalculationParameters |
| GET | /calculation-operations | ListCalculationOperations |

CreateFeed принимает только name/code/export_settings: всегда создаётся пустой
DRAFT. Передать definition/schema/status/id/version нельзя.
Карточка GET возвращает schema, export_settings, version, ID, статус и даты.
Редактор рабочей схемы реализован в срезе 1.3.3. Поле передаёт общие свойства и type_definition с
дискриминатором kind по разделу 4. STRING/TEXT принимают locale/fallback,
MONEY — необязательную currency (null или код); неизвестные/чужие свойства отклоняются, в том числе
старые плоские value_type/locale/currency. export_settings.product_mode принимает
только VARIABLE_TO_SINGLE и по умолчанию получает это значение при создании.
GetFeed возвращает его явно; null/неизвестные коды отклоняются. Вход преобразуется
в FeedProductMode на границе до вызова Domain. PATCH различает отсутствие настройки
и явное значение, в первой версии альтернативных режимов нет.
CreateFeed требует export_settings и обязательное format_settings внутри него,
без default формата. format_settings — один объект с дискриминатором format=csv/xml
и параметрами соответствующего типа, как в разделе 5.2. Неизвестные/чужие свойства,
None/null, коллекции и старая форма formats отклоняются. На границе создаётся
один VO без передачи ClassVar format в конструктор. GET возвращает выбранную
конфигурацию. Метаданные активного файла читаются отдельным GET экспорта.
Для PATCH format_settings заменяет объект целиком, отсутствие сохраняет его,
null недопустим; смена формата не заменяет активный файл до успешной генерации.
Реализованы отдельные controller/request/response каждого метода; у DELETE нет
пустого Response-класса. Prefix и router подключены к src/modules/router.py.
UpdateFeed получает expected_version и хотя бы одно из name/code/export_settings.
Пропуск свойства сохраняет его, null запрещён. export_settings заменяется целиком.
Список принимает search (до 255 символов), status, limit=50 (1..100), offset>=0
в диапазоне BIGINT. Поиск по имени/коду не учитывает регистр и экранирует wildcard.
Сортировка updated_at DESC, id DESC; ответ items/total/limit/offset.
Обычный список исключает ARCHIVED; явный status=ARCHIVED возвращает архив.

POST возвращает 201; GET/PATCH — 200; DELETE — 204 без тела.
404 — отсутствующий Feed в текущем tenant; 409 — занятый код, устаревшая версия
или изменение архива; 422 — неверные данные/пустой PATCH/некорректная версия.
Аутентификация/CSRF — существующие зависимости Identity. require_feed_access
проверяет tenant-контекст и AuthorizationService.can для resource_type=feed_builder.feed
с действиями feed_builder.feed.create/read/update/archive. Клиент не выбирает SQL-схему.
UoW завершается до отправки ответа; ошибка не превращается в успешный CRUD.
Схема сохраняется и возвращается в
единственной форме type_definition без параллельных aliases. Реестры /field-types
описывают возможности типов для UI и не заменяют типизированную схему параметрами
вида {name, value}. Предустановленные схемы появятся позднее через применение пресета.
ListSourcePaths выдаёт только источники из Domain-контракта с метаданными доступа
и совместимости. Входные provider/path преобразуются в Enum на границе, свободного
ввода путей нет; прямой запрос также проходит серверную проверку.

#### **12.1.1. Реализованный API рабочей схемы**

GET /feeds/{id}/schema возвращает feed_id, общую version, status и definition.
PUT /feeds/{id}/schema/draft принимает только expected_version (положительный
BIGINT) и полный definition. Сегмент `/draft` сохранён для совместимости с
Console. Метод записывает актуальную схему в Feed, а expected_version — это
текущая `Feed.version`.
Ответ 200: feed_id/version/канонический definition; no-op сохраняет версию/дату.
PATCH настроек не меняет схему, сохранение схемы не меняет настройки/статус.
Одновременные изменения обоих экранов защищаются одной Feed.version.

Закрытые Pydantic-описания различают текст/деньги, источники, преобразования и все
известные узлы AST. Лишние поля, неизвестные пути, старые aliases и числовые JSON
значения вместо Decimal-строк отклоняются. До JSON decoding проверяется лимит
тела 1 МиБ, включая chunked-запросы, и ограничение вложенности; Domain сохраняет
свои бюджеты AST/полей/правил/литералов. Сохранение схемы не исполняет выражения;
вычисление выполняется отдельным read-only preview после семантической проверки.

FeedSchemaSourcePolicy проверяет совместимость пути с типом. TITLE/DESCRIPTION
требуют локаль; SKU не принимает locale/fallback; REGULAR_PRICE совместим с MONEY.
Application проверяет основную и fallback-локали одним обращением к owner-порту
reference_data через SchemaLocalesPort. Валютная метка проверяется CurrencyVO
без обращения к курсам или справочнику валют. Внешние данные товаров не читаются.

Сохранение использует feed_builder.feed.update; чтение и метаданные —
feed_builder.feed.read. Аутентификация, tenant admission, CSRF и внешний UoW
остаются существующими. 409 имеет code VERSION_CONFLICT или FEED_ARCHIVED;
404 — FEED_NOT_FOUND; предметный 422 содержит code SCHEMA_INVALID, message,
field_id и path, если поле определимо. Ошибки HTTP-формы возвращают validation loc.
Сбой commit не превращается в успешный ответ, изменения откатываются.

GET /field-types возвращает типы, editable_modes SOURCE/MANUAL (для MONEY также
CALCULATED), активные локали,
max_fields/max_transforms. GET /source-paths описывает четыре Domain Enum пути,
допустимые типы и требование локали. GET /transforms описывает существующие
string.trim/string.truncate/money.ceil_step и конкретные типы их параметров.
Пути вводятся выбором из реестра; произвольного URL или Python-атрибута нет.

#### **12.1.2. Реализованный API расчётного предпросмотра**

Префикс /api/console/feed-builder:

| Метод | Путь | Результат |
| --- | --- | --- |
| GET | /calculation-parameters | ID, тип, nullability и подпись пяти подключённых параметров |
| GET | /calculation-operations | Операции/арность, engine_version, precision и лимиты |
| POST | /feeds/{id}/calculation-preview | Read-only расчёт текущего MONEY-поля на позиции Catalog |

POST принимает expected_version (текущую Feed.version), field_id,
catalog_item_id, catalog_variant_id=null либо UUID выбранного варианта и optional
полное definition_override этого поля в существующем HTTP-формате. Допускается
новое несохранённое поле с собственным ID; временная схема проверяет уникальность
его ID/key/export.name. Передать цены, as_of или произвольные пути нельзя.

Ответ содержит feed_id/version/field_id, definition_hash канонического определения,
оба Catalog ID/selected_product_id/product_kind/sku, фактическую (пассивную) source_revision,
as_of/valid_until, calculation_engine_version, validation_status VALID/INVALID,
resolved_value, selected_rule_id/used_default, steps, parameters и issues с
field_id/rule_id/path. Суммы передаются строками; при отсутствии валютной метки
resolved_value содержит только amount.

Сначала проверяются feed_builder.feed.read, feed_builder.feed.calculation_preview
и catalog.item.read для выбранного корня/варианта. Metadata требует Feed read;
POST защищён существующими auth/tenant/CSRF и лимитами тела 1 МиБ/depth.
source_revision отражает фактическое SQL-поле Catalog. Сейчас оно пассивное и
при PATCH цены не увеличивается, поэтому не является маркером свежести/ключом
кеша. Preview перечитывает цену при каждом вызове, показывает снимок на as_of;
смена самой цены при прежнем revision отражается следующим расчётом. Перед
постоянными проекциями публикаций нужен отдельный согласованный механизм
инвалидации Catalog (монотонная версия или fingerprint/события), без выдуманных
версий в этом срезе.
404 означает недоступный Feed/товар/пару; 409 — версия/архив; 422 — форма/семантика
определения; 403 — права; 503 — техническая недоступность источника. Ошибка
исполнения корректного AST возвращает 200 с INVALID и адресованными issues,
не маскируется переходом на ELSE. Preview не делает write/invalidation как мутация.

### **12.2. Публикации**

Реализованы под /api/console/feed-builder:

| Метод | Путь | Сценарий |
| --- | --- | --- |
| POST | /feeds/{id}/publications | AddCatalogItems, атомарный пакет до 100 |
| GET | /feeds/{id}/publications | ListPublications, серверные search/status/locale/limit/offset |
| GET | /publications/{id} | GetPublication, карточка участия |
| GET | /publications/{id}/fields | GetPublicationFields, режимы и значения полей |
| PUT | /publications/{id}/overrides/{field_id} | SetPublicationOverride, валидация и сохранение |
| DELETE | /publications/{id}/overrides/{field_id} | ResetPublicationOverride, возврат к схеме |
| PATCH | /publications/{id}/status | ChangePublicationStatus: ENABLED/PAUSED |
| DELETE | /publications/{id} | RemovePublication через архив |
| POST | /publications/{id}/restore | RestorePublication с проверкой доступности Catalog |
| GET | /feeds/{id}/variant-selection/{catalog_item_id} | Фиксированный набор всех текущих вариантов |

POST добавления возвращает 200 с CREATED/EXISTING, не обрезает и не раскрывает
VARIABLE автоматически. DELETE принимает expected_version в query и возвращает
204 без фиктивной response schema. PATCH/restore принимают expected_version
публикации в теле и возвращают id/status/version/updated_at. Версия Feed используется
только при добавлении; изменения публикаций не увеличивают её.
Список содержит feed_version/feed_status, items/total и счётчики статусов всего
Feed; по умолчанию архив исключён. Сведения об источнике ограничены парой ID,
kind/title/parent_title/sku/source_available. Readiness не выдумывается.

Каждый метод имеет отдельные controller/request/response и Application-сценарий;
общие зависимости используют один UoW. Права Feed read и publication.read/add/
update/archive/restore проверяются через Identity с ресурсом Feed. Подписи/выбор
требуют Catalog read; список проверяет также право чтения коллекции, включая
поиск/счётчики без строк. Все выбранные корни/варианты проверяются отдельно.
Изменения защищены CSRF; тела ограничены до JSON/Pydantic. 404 — недоступный объект/
пара, 409 — версия/переход/архив Feed, 422 — структура/лимит, 403 — права,
503 — техническая недоступность Catalog. Архив Feed доступен для чтения состава.

В variant-selection владелец Catalog читает набор ID и размер семейства одним SQL
снимком. Более 100 вариантов дают 422 с предложением индивидуального выбора;
недоступное семейство — 404. После получения снимка submit передаёт эти конкретные
пары; добавленные позднее варианты не включаются. API snapshot сам ничего не пишет.

Для подробного расчёта цены из карточки используется POST /feeds/{id}/calculation-preview.
Для редактирования ручных значений GET /publications/{id}/fields читает одно
состояние схемы и публикации. PUT принимает обе версии и строку значения в теле.
DELETE принимает обе версии в query. Конфликт возвращает 409 без записи.

### **12.3. Экспорт и публичная ссылка**

Административные маршруты используют префикс `/api/console/feed-builder`.

| Метод | Путь | Назначение |
| --- | --- | --- |
| POST | /feeds/{id}/export/refresh | RequestFeedRefresh. Принимает expected_version, возвращает 202 и текущее состояние задачи |
| GET | /feeds/{id}/export | GetFeedExportState. Текущая задача, последний отчёт и URL активного файла |
| GET | /feeds/{id}/export/issues | ListLatestFeedExportIssues. Диагностики последнего отчёта с фильтрами и пагинацией |
| POST | /feeds/{id}/public-link/rotate | RotateFeedPublicLink. Принимает expected_version, возвращает новую ссылку |

Публичный `GET /api/public/feed-builder/{public_link_id}/feed.csv` находится
в отдельном router на хосте tenant. В admin API права и CSRF применяются
по правилам Console. Публичный API проверяет условия раздела 11.5 и отдаёт
поток без admin-сессии. URL для скачивания и секреты будущего PRIVATE
имеют отдельные контракты.

### **12.4. Preview DTO и объяснение цены**

Backend возвращает publication_id, catalog_item_id/catalog_variant_id,
status/readiness, версии Feed и публикации,
as_of, метаданные расчёта и поля. Пример одного поля ниже: trace без разрешения на
закупочные данные, поэтому исходные защищённые суммы в нём отсутствуют.
value_type/currency здесь — производные свойства DTO результата из
FieldDefinition.type_definition.kind/currency, а не вторая копия настроек в Domain
или входная форма схемы. То же относится к типу ExportCell.
При отсутствии метки currency в определении равна null, а в результате/экспорте
код не передаётся: resolved_value содержит только {"amount": "1250.0000"}.
Override принимает только {"amount": "..."} без собственной currency.

```json
{
  "field_id": "33333333-3333-4333-8333-333333333333",
  "key": "partner_price",
  "label": "Партнёрская цена",
  "value_type": "money",
  "currency": "UAH",
  "origin": "CALCULATED",
  "override_value": null,
  "resolved_value": {"amount": "1250.0000", "currency": "UAH"},
  "calculation_trace": {
    "rule_id": "77777777-7777-4777-8777-777777777777",
    "used_default": false,
    "details_redacted": true,
    "rounding": {"operation": "money.ceil_step", "step": "0.1"}
  },
  "validation": {"status": "VALID", "issues": []},
  "can_override": true,
  "can_reset": false
}
```

С разрешением trace раскрывает пройденные условия, параметры/ревизии,
использованную формулу и числовые шаги. Доступ только к конечной цене
не даёт автоматически доступ к исходной закупке. Политика разрешения формул
с защищёнными входами описана в разделе 14; финальная цена может сама раскрывать
производные сведения, это учитывается правами на настройку/экспорт.

### **12.5. Ошибки и версии запросов**

Transport envelope: code, message, field_id?, rule_id?, expression_path?,
details, request_id. Он не заменяет DTO успешных результатов разных use cases.
Коды включают FEED_NOT_FOUND, INVALID_SCHEMA,
UNKNOWN_FIELD, UNKNOWN_SOURCE_PATH, SOURCE_TYPE_MISMATCH,
REQUIRED_VALUE_MISSING, MAX_LENGTH_EXCEEDED,
TRANSLATION_MANUAL_REQUIRED, VERSION_CONFLICT, SOURCE_UNAVAILABLE,
UNKNOWN_CALCULATION_PARAMETER и вычислительные коды раздела 8.6.

Запись передаёт `expected_version` изменяемого агрегата. Сохранение схемы,
предпросмотр, пробный CSV и будущий запрос генерации принимают обязательную
положительную `Feed.version`. Сохранение возвращает актуальную версию Feed.
PATCH различает отсутствие поля и null. Создание — 201, постановка задания — 202,
операция без результата — 204 без фиктивной response schema. Reset возвращает
новую версию, поэтому для него используется 200 с конкретным DTO.

Нет ресурса — 404, конфликт — 409, недопустимый ввод/definition — 422,
техническая недоступность — 503, неожиданная внутренняя ошибка — 500.
Проблемы вычисления корректного preview возвращаются в issues, а не маскируются
как транспортная ошибка. Списки/trace/preview имеют серверные лимиты и пагинацию.

## **13. Frontend: конструктор, условия и предпросмотр**

### **13.0. Реализованный Console Feed CRUD**

Модуль frontends/apps/console/src/modules/feed-builder подключён через публичный
index.ts к authenticated workspace routes и разделу «Каналы продаж → Фиды».
Реализованы /feed-builder/feeds, /feed-builder/feeds/new и /feed-builder/feeds/:id.
Они используют существующий /api/console/feed-builder/feeds через общий HTTP client
и CSRF, без изменений серверных контрактов.

Список показывает название, код, формат, статус, число полей и дату обновления.
Поиск по названию/коду, статус и offset сохраняются в URL; размер страницы — 50,
сортировка серверная, фиксированная. «Все рабочие» исключает архив, «В архиве»
запрашивает ARCHIVED. После архивации последней строки offset возвращается
на последнюю существующую страницу. Возврат из настроек сохраняет фильтры списка.

Создание требует name, code и явно выбранный CSV/XML. Форма показывает настройки
одного формата: CSV delimiter/include_header либо XML root_name/item_name.
Кодировка UTF-8, VARIABLE_TO_SINGLE и STRICT фиксированы. Новый Feed — DRAFT
с пустой схемой; после POST открывается его карточка.

Карточка редактирует только name/code/export_settings. PATCH содержит отличия
и expected_version открытого снимка; export_settings заменяется целиком.
schema/status/version не редактируются формой. Draft отделён от query cache:
refetch не стирает ввод, успешный ответ подтверждает только отправленный снимок.
409 сохраняет ввод и требует явной загрузки актуальных настроек перед повтором;
версия не подставляется в повторный PATCH автоматически. Уход с несохранённым
вводом требует подтверждения, pending блокирует повторную отправку.

Архивация доступна в списке и карточке после подтверждения с названием/кодом.
expected_version фиксируется при открытии диалога и не меняется при refetch.
После 204 списки/карточка помечаются устаревшими, список перечитывается;
из карточки выполняется возврат в список. Конфликт в диалоге требует закрыть
его и проверить данные. Архивный Feed доступен только для просмотра, код занят,
восстановление и физическое удаление не предлагаются.

DTO/mapper, чистые модели/проверки, query keys, queries, отдельные create/update/
archive composables, draft, page state и UI разделены по архитектуре Console.
Ключи включают tenant/user/sessionRevision и параметры запроса; AbortSignal
передаётся в HTTP. Смена контекста очищает draft/диалоги/старый cache, отменяет
запросы и отклоняет поздние ответы, включая возврат к прежнему tenant.
POST не повторяется автоматически: при неоднозначном результате форма блокирует
повторное создание и предлагает проверить список. 403/404/422/409 имеют понятные
сообщения; UI не разбирает Axios. Редактор схемы добавлен в 13.2.
Управление ассортиментом описано в 13.4. Сборка файла и публичная ссылка входят
в срез 16.7. Приватные ключи подключаются в 16.8.

### **13.1. Создание Feed**

Форма содержит name, code и настройки выбранного формата. В Export Settings показано
описание «Варианты как самостоятельные товары»; единственный код модели —
VARIABLE_TO_SINGLE по умолчанию. Выбор между режимами в первой версии не нужен.
DTO и чистая модель сохраняют явный код режима. Форма требует явный выбор CSV
либо XML без предвыбранного формата; одновременно выбрать два нельзя. Показываются
настройки только выбранного варианта. До выбора submit недоступен, backend также
проверяет обязательность. Чистая модель — объединение по format; UI получает
настройки через props и emits изменения, API mapper собирает один format_settings.
Смена выбора заменяет конфигурацию, без коллекции/флагов formats и общих csv/xml.
Backend создаёт Feed с пустым составом. Пустое состояние объясняет добавление
полей; title/description/price
не добавляются автоматически. Нет выбора общей валюты/локали вычислений или
обязательной отдельной ценовой политики.

### **13.2. Конструктор схемы**

Текущий маршрут /feed-builder/feeds/:id/schema доступен через вкладку «Схема»
в карточке Feed; существующая ссылка /feeds/:id открывает настройки.
Палитра добавляет пользовательское поле, список выбирает/дублирует/удаляет и
переставляет его доступными кнопками. Копия получает новый UUID/key/export.name,
переименование/перестановка сохраняют ID. Удаление подтверждается пользователем.
Inspector редактирует общие свойства и вложенные настройки выбранного типа.

SOURCE выбирается из серверного реестра, MANUAL задаёт последующее заполнение
публикации и не содержит значения в схеме. MONEY допускает пустую валютную метку.
Числовые денежные границы и шаги хранятся строками; текстовые длины сохраняют
незавершённый ввод локально до валидации. Для текста доступны локаль, fallback и
упорядоченная цепочка запасных локалей. Порядок transforms редактируется отдельно.
CALCULATED редактируется визуальным деревом: параметры/Decimal-константы,
арифметика/функции, сравнения/наличие/логические группы, упорядоченные IF и ELSE.
Редактирование/перестановка сохраняют ID правила, копирование создаёт новый UUID.
Быстрые действия «прибавить процент/сумму» строят AST для ELSE без локального расчёта.
`price.purchase` и `product.category_ids` доступны через серверные метаданные.
Определения с устаревшими неподдерживаемыми конструкциями сохраняются вместе
с AI-метаданными при редактировании остальных полей.

«Сохранить схему» проверяет локальный черновик и сохраняет полное определение
в Feed. После успешного ответа это актуальная схема следующего запуска.
Невалидный/незавершённый ввод остаётся в форме; ошибки связываются с полем,
первое проблемное поле выбирается и control получает focus. Refetch не стирает
изменения; 409 сохраняет ввод и требует явной загрузки актуальных данных.
Успешный ответ подтверждает только отправленный снимок. Pending блокирует дубль,
выход с dirty требует подтверждения. Архив — read-only. Смена tenant/session
очищает draft/cache/выбор, отменяет запросы и отклоняет поздние результаты.
Схема, настройки и список Feed инвалидируются после сохранения; число полей
читается из сохранённого определения. Серверный кеш — Vue Query, не Pinia.

Предпросмотр MONEY показывает поиск и страницы товаров Catalog, язык названий,
отдельный выбор VARIANT у VARIABLE, результат/ветвь/исходные параметры/trace/issues.
Он передаёт текущий draft поля без предварительного save. Изменение поля, выбранной
позиции, Feed.version или блокировка редактора отменяют запрос и помечают прежний
результат устаревшим; поздние ответы (включая переход A→B→A) игнорируются.
После valid_until результат устаревает по таймеру; при скрытии/повторном открытии
экрана требуется свежий расчёт, а не обещание вечной актуальности source revision.
Смена tenant/session очищает результат/выбор и scoped caches, dispose снимает таймеры.
Денежного evaluator на frontend нет: Console только строит AST и показывает серверный ответ.

Дальнейший целевой конструктор:

Три зоны: FieldPalette (STRING/TEXT/MONEY), упорядоченный SchemaCanvas и Inspector.
Каждое добавление создаёт новый UUID; переименование/перестановка сохраняют ID.
Все поля можно удалять по общим правилам, special-key проверок нет. Required —
проверка обязательности значения публикации во время resolve.

Inspector: key/label/type, язык либо валюта результата, способ получения значения,
fallback, constraints, transforms и export. Смена смысла сохранённого ID
показывает необходимость нового поля, но пользователь не обязан создавать новый Feed.
Дерево будущих групп/массивов не имитируется неработающими элементами MVP.

Page оркестрирует toolbar/save/preview, palette/canvas/inspector — UI
с props/emits. Локальный draft composable владеет полной формой/AST и dirty snapshot.
Реестры источников/операций/параметров/типов приходят с backend.
Чистая клиентская модель поля — discriminated union по type_definition.kind:
string/text содержат текстовые настройки, money — денежные. Inspector изменяет
этот вложенный вариант, без параллельных value_type/locale/currency на поле и без
нетипизированного массива {name, value}. Неполный ввод остаётся локальной формой;
перед сохранением собирается полный допустимый вариант по разделу 4.

### **13.3. Редактор денежного поля**

```text
MoneyFieldInspector
  ├── CurrencyLabel: optional
  ├── ValueMode: SOURCE / CALCULATED / MANUAL
  ├── SourceSettings (SOURCE)
  ├── CalculationEditor (CALCULATED)
  │    ├── DefaultExpressionEditor (ELSE)
  │    └── OrderedRuleList
  │         └── Rule: ConditionBuilder (IF) + ExpressionEditor (THEN)
  ├── Transforms / Rounding
  ├── Constraints / Export
  └── TestOnProduct → серверный preview/trace
```

Правило можно добавить/отредактировать/удалить/переместить с сохранением rule_id;
копия получает новый ID. Видно «первое совпадение», обязательный ELSE и отсутствие
автоматического суммирования правил. Category selector показывает labels и
сохраняет UUID в условии. Редактор предлагает `price.purchase` в списке параметров.
При предпросмотре значение берётся из выбранной позиции Catalog.

Кнопки «+процент», «+сумма», «формула» строят типизированный AST. Числа/суммы
хранятся Decimal-строками без валюты. Пользовательский курс — обычная числовая константа. Визуальный редактор
поддерживает скобки, операции и разрешённые функции; не исполняет Python/JS.
Если есть текстовое представление, оно разбирается ограниченной грамматикой в тот
же AST; при отсутствии такого parser UI остаётся визуальным. Единственный
сохраняемый источник истины — дерево, не две расходящиеся версии строки и AST.

Preview показывает выбранную ветвь/ELSE, условия, формулу, разрешённые параметры,
деление/умножение и другие операции, округление и результат. Ошибки привязаны к field_id/rule_id/path.
Backend исполняет арифметику; frontend может проверять форму, но не рассчитывает
вторую независимую «правильную цену». Несохранённый AST проверяется через preview
override без изменения сохранённой схемы.

### **13.4. Публикации и overrides**

Реализована вкладка «Товары» и маршрут /feed-builder/feeds/:id/publications.
Список показывает Catalog title/SKU, родительскую карточку варианта, участие,
дату добавления и действия. Поиск/статус/локаль/страница хранятся в URL;
сервер возвращает ограниченную страницу. Карточка открывается через query
publication=UUID и восстанавливается по ссылке/reload.
Пауза/возобновление, подтверждённые архивация/возврат сохраняют publication_id.
Архив Feed read-only. Повторное добавление отображает CREATED/EXISTING, сообщает
о сохранённых PAUSED/ARCHIVED и предлагает открыть архив для явного возврата.

Диалог получает SIMPLE и VARIABLE через публичный frontend-контракт Catalog.
У SIMPLE свой флажок, у VARIABLE — список отдельных вариантов. Выбор сохраняется
между страницами/поиском/семействами до submit. «Все существующие» получает полный
ограниченный снимок ID; запрос отменяется при смене контекста, поздние ABA-ответы
игнорируются. Превышение общего выбора 100 не меняет предыдущий набор.
Pending блокирует повтор submit; 409 сохраняет выбор и требует явного обновления
контекста Feed. Смена tenant/session очищает выбор/результаты и scoped caches.
После неоднозначного ответа интерфейс предлагает проверить состав перед повтором.

В карточке пользователь выбирает MONEY-поле сохранённой схемы и проверяет цену
конкретной публикации: сумма, необязательная валютная метка, IF/ELSE, inputs/trace/
issues/as_of. Нет скрытого выбора по key=price и общего статуса READY на основании
одного денежного поля. Раздел «Поля публикации» отдельно показывает значение
по схеме и даёт сохранить или сбросить ручное значение для каждого поля.

Вкладка «Предпросмотр» показывает рассчитанные экспортируемые поля до 20
ENABLED-публикаций и позволяет скачать пробный CSV по всему включённому
ассортименту. Ручные значения учитываются в карточке, предпросмотре и CSV.
Фильтрация по готовности относится к материализованным проекциям.

### **13.5. Экспорт, последний отчёт и ссылка**

Экран «Экспорт» показывает текущую пересборку, дату расчёта активного файла,
публичную ссылку и результат последней завершённой проверки. В отчёте
показываются счётчики успешных позиций, позиций с предупреждениями и с ошибками,
диагностики по полям и итог обновления файла. Во время нового запуска виден
предыдущий завершённый отчёт. Если файл ещё не создан, экран предлагает
запустить первую сборку.

Действия «Обновить фид», «Скопировать ссылку» и «Заменить ссылку» используют
сохранённые настройки и права Console. Пока задача активна, повторный запуск
заблокирован интерфейсом. Состояние восстанавливается после перезагрузки
по GET экспорта. Если проверка отклонена, экран сохраняет публичный адрес и
показывает дату файла, который выдаётся по нему.

### **13.6. Модульная структура и кеш**

```text
frontends/apps/console/src/modules/feed-builder/
  api/<entity>.api.ts, <entity>.dto.ts, <entity>.mapper.ts
  model/<entity>.types.ts, <entity>.query-keys.ts
  model/queries/, mutations/, state/
  pages/
  ui/page/, results/, item/, forms/
  routes.ts, index.ts
```

API использует общий Axios client/CSRF, DTO точно отражают backend, mapper чисто
преобразует значения. Decimal не превращается в Number/float. Queries возвращают
frontend-модели, передают AbortSignal, keys включают tenant, ID и версию Feed,
фильтры/пагинацию и входы preview. Any не заменяет типизированное дерево.

Server state — TanStack Vue Query, session — существующие stores. URL/page state
владеет поиском/пагинацией/вкладками; форма — несохранённым draft и полями.
Refetch не стирает ввод. Save очищает только отправленный snapshot, сохраняя
изменения во время запроса. 409 показывает конфликт и позволяет сохранить свой ввод.

Сохранение схемы или настроек инвалидирует затронутые detail/list/schema/preview
keys. Изменение override затрагивает карточку и статистику. Предпросмотр работает
на чтение. Повторный submit
заблокирован pending; неоднозначное создание не повторяется с риском дубля.
Смена tenant отменяет запросы, очищает старый draft/cache, игнорирует поздние ответы.
Опрос состояния экспорта останавливается при завершении задачи и уходе со страницы.

### **13.7. Page/UI, доступность и состояния**

Page собирает state/queries/mutations/router/dialogs, обычный UI использует
props/emits/чистые модели без API/DTO/router/session imports. Общие компоненты
не получают бизнес-логику. Используются semantic tokens, layouts, shadcn-vue
и существующий custom UI Console. Чужие модули доступны только через публичные
контракты, их внутренние stores/query keys не импортируются.

Body различает loading/empty/error/retry/results и сохраняет полезные данные
при background refetch. Есть pending/disabled/errors формы, понятные labels,
focus/keyboard navigation и мобильная адаптация. Перестановка полей/правил имеет
доступные клавиатурные действия. Переход с несохранённым draft защищает ввод.
Presets/AI/форматы площадок не показываются как готовые функции MVP.

## **14. Безопасность, tenant isolation и наблюдаемость**

Tenant-таблицы fb_* используют существующие tenant-aware connection/UoW.
Публичный маршрут определяет tenant по доверенному хосту через Tenancy
admission и ищет текущий идентификатор ссылки в схеме этого tenant.
Доступ к выбранной позиции Catalog проверяется в доверенном tenant-контексте.
Данные Catalog читаются через публичные контракты.

Права разделяют просмотр/редактирование Feed, схемы/формул, overrides,
обновление файла, замену ссылки и доступ к защищённым параметрам Catalog. Для использования `purchase_price`
в расчёте и публичном результате проверяются права на закупочную цену Catalog.
Отдельно проверяется доступ к детальному trace с защищёнными входами.
Скрытие столбца в UI не заменяет backend-проверку; произвольная формула, condition
и definition_override не обходят запрет доступа. Пресеты будущего не повышают права.

Источники/параметры/операции зарегистрированы. JSON/AST не содержит исполняемых
Python/JS/SQL, произвольного URL, доступа к файлам или окружению. Лимиты:
байты definition до декодирования, поля/правила/узлы/глубина, длины literals,
коллекции условий, preview, batch, конкурентность задач и время/бюджет evaluator.
Перед постановкой генерации структура и типы проверяются во всех ветвях AST.

CSV имеет явную политику значений, похожих на формулы таблиц, без молчаливого
искажения машинного импорта. XML экранируется, имена/символы валидируются.
Доступ к активному файлу проверяется до streaming и до условного ответа из кеша.
Публичная ротация отключает старый адрес. Будущий PRIVATE хранит только digest
токенов, выдаёт секрет один раз и исключает его из access/application logs.

Domain не логирует. Application/worker логируют безопасные tenant/feed/job
IDs, попытку, длительность и reason_code. Committed — после успешного commit;
один технический сбой со stack trace записывается на одной границе. В логи не
передаются целиком DTO/AST/trace, закупочные суммы, токены и персональные данные.

Метрики: размер/длительность генерации, queue/lease/retry/fencing, FAILED,
число issues/экспортированных товаров, возраст активного артефакта, STALE,
время evaluator, batch/query count. Ожидаемая ошибка значения не становится
технической ERROR автоматически. Cleanup учитывает активные ссылки на файлы
и живые задачи. Временный staging и устаревшие файлы очищаются штатно.

## **15. Тестирование и проверка плана**

### **15.1. Первый срез: только объекты Domain Feed**

Unit-тесты обычного Python без PostgreSQL/FastAPI/HTTP:

- Feed.create с пустым составом не создаёт title/description/price и иные примеры.
- Feed.restore сохраняет ID, состав, порядок, статусы, настройки и даты.
- FeedExportSettingsVO требует один format_settings без default; Feed.create и
  Feed.restore требуют export_settings. Пропуск аргументов не выбирает формат
  автоматически, явный None отклоняется. Пустая схема с выбранным форматом допустима.
- CSV либо XML с нестандартными параметрами сохраняется через create/restore вместе
  со всеми полями Feed, датами, Product Mode и validation_policy.
- CsvExportSettingsVO/XmlExportSettingsVO имеют фиксированный ClassVar format;
  нельзя передать противоречащий format конструктору. У FeedExportSettingsVO нет
  formats/csv/xml-свойств. Enum/строки/dict, null и коллекции любого размера вместо
  одного VO отклоняются. Настройки и вложенные VO неизменяемы.
- FeedProductMode содержит только VARIABLE_TO_SINGLE. FeedExportSettingsVO и
  Feed.create с явно выбранным форматом используют его по умолчанию; настройки и
  Feed.restore сохраняют Enum вместе со всеми остальными свойствами. Сырые строки,
  null, чужие Enum и неизвестные значения отклоняются; внешних чтений для этого нет.
- FieldDefinition/ConditionalPriceRule имеют create/restore без __post_init__;
  восстановление не генерирует новые ID/не создаёт события.
- Каждый VO проверяет своё значение, frozen-структуры неизменяемы глубоко;
  входной mutable список/словарь не меняет созданный объект.
- ID/key/export.name и rule_id имеют нужную уникальность; поля равноправны.
- Required не делает поле неудаляемым или обязательным в каждой схеме.
- FieldDefinition содержит только общие свойства и type_definition; прежних
  плоских настроек нет. kind фиксирован классом VO и не принимается конструктором.
- Все три типа сохраняют свой полный состав через FieldDefinition.create/restore
  и Feed.create/restore. SKU без locale допустим; currency у MONEY может отсутствовать или быть None.
- SourceReferenceVO принимает SourceProvider.CATALOG и четыре CatalogSourcePath;
  коды catalog/item.title/item.description/item.sku/item.regular_price стабильны.
  Сырые строки, неизвестные значения, чужие Enum с совпадающими кодами и
  несовместимые типы provider/path отклоняются с InvalidFeedValueError.
- Схема короткого/длинного текста, SKU и цены сохраняет именно экземпляры Enum
  через create/restore поля и Feed. Ссылка неизменяема, внешних чтений нет.
- Нельзя передать currency тексту, locale/fallback деньгам, денежные границы тексту,
  длины деньгам либо чужие value_definition/transforms. Нельзя передать dict вместо VO.
- TextConstraintsVO/MoneyConstraintsVO проверяют только свои границы; transforms
  копируются в tuple и ограничены бюджетом. Нет двух способов получения значения одновременно.
- Формулы/условия корректно представлены типизированными узлами, арность/enum/
  Decimal/literal/параметры VO проверены; ELSE обязателен для CALCULATED.
- Пустой список rules допустим; порядок/UUID сохраняются после restore.
- Собственные настройки проверяют VO типов. PriceCalculationStructurePolicy
  проверяет ID и бюджет AST при create/restore поля и восстановлении
  Feed без выбора ветви, вычислений и обращения к внешнему реестру параметров.
- Нет evaluator, редактора полей, генерации, событий и запросов
  к справочникам. Репозиторий и внешние слои есть только у Feed CRUD.

Это критерии первого среза. Исполнение IF и арифметики, а также проверки
пригодности схемы к экспорту относятся к следующим срезам.

#### **15.1.1. Domain-проверки публикации и экспорта**

Существующие проверки `FeedPublication` сохраняются. Они покрывают
типизированную ссылку SIMPLE/VARIANT, уникальные overrides по `field_id`,
точные денежные значения, различие явного пустого значения и отсутствия
override, даты и сохранность состояния.

При замене объектной модели генерации тесты экспорта проверяют:

- Одно `FeedExportState` на `feed_id`. Незавершённая задача, последний отчёт
  и активный файл могут существовать одновременно.
- Снимок и `as_of` сохраняются при повторе активной задачи. Завершение очищает
  данные задачи. Устаревший `job_id` не меняет результат.
- Полный отчёт согласует счётчики. Технический сбой может дать неполные данные.
  `REJECTED` и `FAILED` оставляют активный файл прежним.
- Успех заменяет активный файл целиком. Проверяется типизированная ссылка
  на файл и соответствие формата снимку.
- Ротация ссылки меняет её идентификатор внутри Feed независимо от файла.
- Архитектурные тесты проверяют чистый Domain, типизированные ID, границы
  репозиториев и переходы через методы агрегатов.

#### **15.1.2. Реализованный Feed CRUD**

test_feed_builder_crud.py проверяет Domain change_settings/archive, версии,
идемпотентность и атомарность, Application-сценарии, закрытые HTTP-контракты
и полный JSON round-trip схемы/AST с Decimal, fallback и nullable currency.
Повреждённые данные не заменяются пустой схемой или CSV.

test_feed_builder_crud_postgres.py выполняется с TEST_POSTGRES_URL на изолированной
PostgreSQL. Проверяются полный HTTP CRUD с реальными auth/CSRF/UoW, архив и
сохранение занятого кода, rollback конфликта, конкурентные PATCH, репозиторный CAS,
две tenant-схемы, поиск/страницы/статусы, сохранность сложной схемы, CSV/XML,
миграция нового/существующего tenant. Чтение карточки не вызывает Feed.restore.

Архитектурные тесты проверяют границы Feed, публикаций и экспорта. `FeedAccessKey`
пока представлен только в Domain. Проверки metadata/registration/tenant-migration
остаются обязательными.

#### **15.1.3. Console Feed CRUD**

Node-тесты test/feed-builder-contracts.test.ts, feed-builder-state.test.ts
и feed-builder-editor.test.ts
проверяют явный выбор формата, закрытый POST, минимальный PATCH/expected_version,
полную замену CSV/XML без смешения настроек, false/tab, XML identifiers,
round-trip Decimal-строк схемы без Number, изоляцию draft и подтверждение только
отправленного снимка, фильтры/offset/безопасный returnTo, разделение query keys
по tenant/user/session, блокировку дубля и позднего ответа отменённого запроса.
Интеграционный тест composable с настоящими Vue/Pinia/QueryClient дополнительно
проверяет refetch/conflict/reset, pending, ввод во время save, очистку прежнего
cache/draft при смене tenant и запрет изменения архивного Feed.
Команда из frontends/: npm --workspace @dnk/console run test:feed-builder
(Node 24, как существующие Console tests).

Обязательны lint:console, typecheck:console, build:console и браузерные проверки
создания/смены формата/архивации/read-only, pending, 409 с сохранением ввода,
403/retry, empty/search/URL/reload, смены tenant, неоднозначного POST,
клавиатуры и мобильного viewport. Браузерная проверка на тестовых ответах API
подтверждает работу клиента и payload, но не заменяет PostgreSQL HTTP-тесты 15.1.2.

#### **15.1.4. Рабочая схема: backend и Console**

test_feed_builder_schema.py проверяет атомарное change_schema/no-op/порядок/ID,
архив, совместимость источников, locale port, лимиты и закрытый HTTP/AST round-trip.
PostgreSQL suite test_feed_builder_crud_postgres.py дополнен полным schema API
workflow, metadata, CSRF/права/tenant, shared-version конфликтом с настройками,
chunked/depth лимитами, rollback при ошибке commit и сохранностью сложного AST.

Console tests feed-builder-schema.test.ts и feed-builder-schema-editor.test.ts
проверяют четыре поля, независимый proxy-safe draft, ID/копии/порядок, незавершённый
ввод, точность Decimal-строк за диапазоном Number, AST/AI round-trip,
refetch/conflict/reset, pending, ввод после submit, смену tenant/session и архив.
Обязательны общие lint/typecheck/build Console и существующие regression tests.

Сквозная браузерная проверка использует реальный Feed API и временную PostgreSQL:
создание CSV → четыре источника → локали/валютная метка/transforms → порядок →
save/reload → копия/удаление → конкурентный PATCH настроек/409 с сохранением ввода →
исправление ошибок/focus → повторное сохранение → архив/read-only. Отдельно
проверяются desktop/mobile, клавиатура, пустая схема, 404 и отсутствие runtime errors.
Auth identity в такой проверке задаётся тестовой фикстурой; CSRF/Feed/UoW/SQL настоящие.

### **15.2. Поведение Domain и вычислитель следующих срезов**

| Сценарий | Ожидание |
| --- | --- |
| Произвольные ключи/состав, в том числе без MONEY | Нет скрытых обязательных полей |
| Переименование/перестановка | field_id сохраняется, состав не теряется |
| Дубликаты/несовместимый старый ID | Операция отклоняется без частичной мутации |
| Схема сохранена во время сборки | Снимок запущенного задания остаётся прежним |
| Формула, условие или порядок изменены и сохранены | Следующее задание использует новое определение Feed |
| Два истинных правила | Выполняется только первое |
| Ни одно правило не подошло | Выполняется default_expression |
| ALL/ANY/NOT | Типы/арность и короткое замыкание соблюдены |
| Ошибка выбранного условия/формулы | Не считается False и не переходит скрыто к ELSE |
| Отсутствие в неприменённой ветви | Не блокирует результат |
| EXISTS/IS_MISSING, 0, False, пустой набор | Отсутствие не смешивается со значением |
| `purchase_price = null`, есть проверка `EXISTS` и ELSE на `price.regular` | Выбирается ELSE |
| `purchase_price = null`, выбранное выражение требует `price.purchase` | CALCULATION_PARAMETER_MISSING |
| `purchase_price = 0` | `EXISTS` истинно, арифметика использует ноль |
| У SIMPLE и у двух VARIANT разные закупочные цены | Для каждой позиции используется её собственная цена Catalog |
| Категория UUID | Точное членство, не имя/не неявные предки |
| `price.regular = 1000`, множитель 1.20 | 1200 до иных transforms |
| `price.purchase = 800`, множитель 1.25, метка поля UAH | 1000 UAH в результате, в Catalog остаётся 800 |
| Sale вне/на границах [from,to) | Корректное отсутствие/выбор effective по as_of |
| Типы денег/чисел, деление на ноль | Предсказуемые результаты/ошибки, без float |
| Пользовательский курс и валютная метка | Пересчёт задан формулой, метка поля добавляется к результату |
| Два денежных поля | Независимые формулы, без общей повторной наценки |
| Ручной override | Сумма без собственной валюты и без формулы; затем transforms/constraints |
| Источник имеет 6 знаков | Все знаки сохраняются, нет автоматического приведения к Shared MoneyVO |
| Неподдержанный AST/версия/операция/цикл ссылок | Отклонение до выполнения |
| Превышен лимит | Структурная или CALCULATION_LIMIT_EXCEEDED ошибка |

Вычислитель проверяется чистыми fixtures snapshots/as_of и числовых формул. Проверяется весь
trace по фактическим ветвям и отсутствие скрытого доступа к источнику/часам.

Проверки выбора и плоского представления в срезах публикаций/экспорта:

- SIMPLE даёт одну публикацию/запись; один выбранный VARIANT — одну; три выбранных
  варианта — три без записи VARIABLE. Смешанный набор обрабатывается общей схемой.
- Выбор только белого топика не добавляет чёрный/коричневый; «Все существующие»
  фиксирует явные ID. Позднее созданный вариант не включается автоматически.
- Повтор добавления, в том числе одиночный выбор плюс «Все существующие», сохраняет
  публикации/overrides/status и не создаёт дубликаты.
- Несуществующий/чужой вариант или VARIABLE без выбранных вариантов отклоняются
  без частичной записи; последующая потеря допустимости видна в readiness.
- Контент наследуется по контракту Catalog в нужной locale; SKU/цена/параметры
  относятся к выбранной позиции. Цена родителя или соседнего варианта не подставляется.
- Preview, формула цены и экспорт используют один контекст варианта; кеши вариантов
  различаются, изменение использованных данных родителя инвалидирует проекцию.

### **15.3. Persistence, конкуренция и изоляция**

PostgreSQL/SQLAlchemy tests: JSONB AST/VO round-trip, Decimal без float,
уникальность простого товара с NULLS NOT DISTINCT и каждой пары родитель/вариант,
round-trip product_mode в настройках/снимке задачи, optimistic versions Feed и
публикации. Проверить атомарную постановку `scheduled_jobs` и `FeedExportState`,
rollback обеих записей, уникальность строки по feed_id и защиту от двойного
запуска. Проверить tenant isolation при чтении Catalog, поиске ссылки и выдаче
файла. Тесты Files покрывают ready lock, защиту текущего `active_file_id` от
удаления и очистку только после смены ссылки.
Restore сохраняет инварианты агрегатов.

Проверить условную запись проекций по ревизиям/времени, valid_until на границе
акции без update-события и инвалидацию при изменении AST, категории или коэффициента
формулы. Отдельно проверить, что добавление, изменение и очистка `purchase_price`
в Catalog делают зависимую проекцию STALE через ревизию выбранной позиции.
EXPLAIN/query count и batch исключают N+1 на каждый товар, поле и узел AST.

### **15.4. Обновление, сериализация и выдача**

- В CSV проверяются порядок колонок, кавычки, переносы, кириллица, Decimal
  и полная обработка ассортимента. `VARIABLE_TO_SINGLE` даёт одну плоскую
  запись на выбранную публикацию.
- Снимок и `as_of` сохраняются при техническом повторе. Старый `job_id` или
  утрата аренды scheduler блокируют фиксацию файла. После исчерпания попыток
  сохраняется отчёт с `FAILED`.
- При изменении схемы или настроек во время сборки результат отклоняется.
  Следующая задача считает по новой конфигурации. Ротация ссылки во время
  сборки сама по себе не делает снимок устаревшим.
- `STRICT` по выборке 90 без замечаний, 5 с предупреждениями и 5 с ошибками
  сохраняет отчёт и прежний файл. При первом таком запуске ссылки ещё нет.
  В режиме `SKIP_INVALID` тот же набор даёт 95 позиций. Если остались только
  предупреждения, оба режима допускают публикацию.
- Первая успешная публикация переводит DRAFT в ACTIVE. Повторная успешная
  публикация сохраняет адрес и меняет содержимое. Предыдущий файл выводится
  из использования и очищается через Files.
- CSV и XML выдаются на зарегистрированном активном хосте без сессии.
  Feed Builder разрешает хост через свой порт и адаптер Tenancy по правилу чтения данных
  (`ACTIVE` или `FREEZE`) и проверяет совпадение с tenant-схемой общего UoW.
  Старый URL после ротации, чужой хост, архивный Feed, несовпадающее расширение
  и отсутствие активного файла не приводят к выдаче. Ротация проверяется с
  условными HTTP-запросами.
- Поток Files закрывается при завершении или обрыве. DB UoW завершается до
  передачи тела, tenant admission удерживается до конца.
- Последующий XML использует тот же worker. При смене формата URL выдачи и
  Content-Type соответствуют фактически активному файлу, XML открывается inline.
- Большой Catalog проходит пакетами с ограниченным staging. Проверяются
  повторы загрузки, сбой до commit, очистка и отсутствие исторических файлов.

### **15.5. API, UI и E2E**

```text
CreateFeed (пустая схема, явно выбранный CSV либо XML)
  → SaveFeedSchemaDraft (пользовательские поля, IF/ELSE/AST)
  → PreviewFieldCalculation
  → AddCatalogItemsToFeed
  → PreviewFeed / DownloadTestCsv
  → SetPublicationOverride / ResetPublicationOverride
  → RequestFeedRefresh из сохранённого Feed
  → scheduled_jobs / jobs worker → ExecuteFeedRefresh
  → Files / Storage → active_file_id
  → Console / последний отчёт → публичный GET на хосте tenant
```

Повторить с двумя Feed с разными формулами, несколькими языками и валютными
метками, категорией, закупочной ценой из Catalog, активной и закончившейся
акцией, ручной ценой, ошибочным новым выражением и сохранением старой выдачи.
При одинаковой схеме, значениях Catalog, overrides и as_of предпросмотр и файл
содержат одинаковую итоговую цену. Tenant isolation и права защищённых входов
проверяются через реальные API и БД.

UI: создание пустого Feed, равноправные поля, порядок IF/ELSE, test-on-product,
trace/errors, loading/empty/error/retry/pending, 409, несохранённый ввод при
refetch/save, URL/reload, смена tenant/поздние ответы, мобильный viewport,
keyboard reorder/focus/labels. Frontend команды из frontends:
`npm run lint:console`, `npm run typecheck:console`, `npm run build:console`,
применимые тесты сценариев. Backend использует принятый runner и статические
проверки проекта без добавления нового тестового фреймворка ради этого плана.

### **15.6. Проверка изменения только документации**

Проверить весь diff по разделу 2.2, относительные ссылки, последовательность
разделов/срезов, закрытие code fences, JSON/AST примеры и отсутствие прежних
контрактов назначения отдельной политики или обязательных полей по имени.
При правке только плана не запускаются сборка приложения/БД/UI тесты и не
создаются файлы модуля. Unit/Integration/E2E пункты выше — будущие критерии реализации.

## **16. Последовательные срезы реализации**

### **16.1. Domain Feed: только корректные объекты**

Feed, FieldDefinition и ConditionalPriceRule с create/restore; VO/enums/ошибки
раздела 3.4, каждый VO в своём файле. Пустая схема, равноправные поля, дерево
условий/выражений, три типизированных VO типов полей, раздельные ограничения,
PriceCalculationStructurePolicy, SourceProvider/CatalogSourcePath и настройки
экспорта с FeedProductMode.VARIABLE_TO_SINGLE по умолчанию и обязательным
format_settings: CsvExportSettingsVO либо XmlExportSettingsVO с фиксированным
ExportFormat. Feed.create требует export_settings; формат автоматически не выбирается.
Коллекции formats и общих csv/xml-свойств нет.
Существующие CurrencyVO/EntityIdVO переиспользуются, локальный PriceAmountVO
сохраняет суммы без валюты и округления; Shared MoneyVO не изменяется, чужие внутренние агрегаты не импортируются.

Не реализуются внутренние методы поведения, evaluator, policies исполнения,
events, repository, Application, SQL, API или UI. Не создаются их пустые заготовки.
Готовность: create/restore и структурные unit-тесты 15.1 проходят без внешних сервисов.

#### **16.1.1. Предыдущий объектный срез Publication, Generation и AccessKey**

В коде предыдущего среза добавлены фабрики и проверки `FeedPublication`,
`FeedGeneration`, `FeedArtifact` и `FeedAccessKey`. Дальнейшая реализация
`FeedPublication` описана в 16.6. `FeedExportState` заменяет объектную модель
генерации в 16.7. `FeedAccessKey` резервируется для последующего PRIVATE.

#### **16.1.2. Первая рабочая вертикаль Feed CRUD — реализовано**

Минимальное поведение frozen Feed, FeedVersionVO, контракт записи; полные
JSON mappers; FeedModel/fb_feeds и tenant-миграция 0020; write/query repositories;
CreateFeed/GetFeed/ListFeeds/UpdateFeed/ArchiveFeed с конкретными DTO;
отдельные HTTP controller/request/response и Depends. Внешний UoW, UUID/Clock,
tenant binding, Identity authorization и CSRF переиспользованы.

Готовность: CRUD работает через /api/console/feed-builder/feeds на реальной
PostgreSQL, ошибки и конкурентные изменения покрыты тестами; JSON round-trip
не теряет существующие поля, nullable currency, точные Decimal и формулы.
Редактор рабочей схемы реализован в 16.1.4; далее — вычисления и поведение публикаций. Ревизии, фоновые сборки
и public distribution в эту реализацию не входят. Console UI вынесен в 16.1.3.

#### **16.1.3. Console Feed CRUD — реализовано**

Список, создание, редактирование настроек одного CSV/XML и архивация подключены
к существующему API. Реализованы URL-фильтры, навигация, read-only архив,
защита draft, version conflict, pending и tenant/session isolation по 13.0.
Контракты/состояние покрыты Node-тестами; применяются проверки 15.1.3.
Редактор рабочей схемы реализован в 16.1.4. Работа с публикациями и генерация
остаются отдельными срезами.

#### **16.1.4. Конструктор рабочей схемы — реализовано**

Завершённый сценарий: создать Feed → открыть «Схема» → добавить пользовательские
STRING/TEXT/MONEY → настроить прямые источники/локали/валютную метку/ограничения/
преобразования/экспорт → изменить порядок → сохранить → открыть повторно →
продолжить редактирование → архивировать и просмотреть read-only.
Backend реализует Domain change_schema/Policy, чистую сборку документа в
Application, read/write порты и SQL-адаптеры, use-case DTO/handlers, закрытые HTTP
схемы и metadata API. Console содержит типизированные DTO/mappers/models,
queries/mutation, отдельный draft и Page/UI. Используется текущая fb_feeds,
новой миграции и истории нет. Исполнение вычислений добавлено отдельным срезом 16.5.

### **16.2. Поведение Domain сохранённой схемы**

Редактирование полей и правил через корень Feed сохраняет идентичность и порядок.
За конкурентную запись схемы, настроек и статуса отвечает Feed.version.
Пустая схема корректна для создания Feed и редактирования.

Готовность: операции атомарны в памяти. Внешние метаданные передаются снимками.
При создании задания пригодная сохранённая конфигурация фиксируется в снимке
генерации по разделу 16.7.

### **16.3. Persistence Foundation**

Tenant Alembic-миграции, SQLAlchemy models, mappers create/restore, write/query
repositories, UoW и версии. Схема хранит AST и
Decimal-константы. Код группируется по корням.

Готовность: round-trip и конкурентные/tenant tests; invariant не перенесён в mapper.

### **16.4. Feed CRUD и конструктор схемы**

Application Command/Query/DTO, Depends, HTTP методы, метаданные типов/источников/
параметров/операций, создание пустого Feed и сохранение актуальной схемы.
Vue Page/model/UI, свободные поля, AST-редактор IF/ELSE, сохранность локального ввода.
Export Settings/API/DTO явно сохраняют единственный product_mode=VARIABLE_TO_SINGLE
и один обязательный format_settings; форма/DTO/API требуют явный выбор CSV либо XML.

Готовность: пользователь создаёт, редактирует и повторно открывает сохранённые
определения. Неподдерживаемые новые определения отклоняются явно.

### **16.5. Формулы цены, IF/ELSE и предпросмотр — реализовано**

Законченный сценарий: открыть MONEY-поле → выбрать CALCULATED → задать IF
sale EXISTS, THEN sale × 1.10, ELSE regular × (1 + 15 / 100) → выбрать товар
SIMPLE либо конкретный VARIANT под VARIABLE → рассчитать текущий ввод → увидеть
цену, выбранную ветвь/исполненные шаги/ошибки → сохранить схему → открыть повторно.
Предпросмотр не добавляет товар в Feed и не создаёт публикаций/генераций/ревизий.

Domain содержит PriceCalculationSemanticPolicy, CalculationInputsVO, PriceValueVO
и MoneyFieldCalculator с адресованными результатами/ошибками/trace. Проверяется
весь AST (включая невыбранные ветви); исполняются только пройденные условия и одна
формула. Ошибка не становится False/ELSE. Отсутствие отличается от 0/False/пустой
строки. Контекст evaluator v1: precision=40, ROUND_HALF_UP, конечный Decimal;
бюджет каждого входа/результата — 40 цифр и exponent ±128, AST depth=32,
nodes=4096, rules=100, collection_items=500. После выражения применяются transforms и constraints.
ceil_step вычисляется точно через целые коэффициенты; скрытого округления по валюте нет.

Первый срез вычислителя подключил price.regular, price.sale (действующая на as_of),
price.effective, product.sku и product.id выбранной позиции.
Новые/изменённые неподдержанные формулы отклоняются семантически; ранее сохранённый
неизменённый AST можно передать при правке других полей без потерь.
Catalog владеет immutable CalculationSnapshot и batch-reader: один SELECT выбранных
ID, проверка ролей/пары родитель-вариант, реальные revision, единый серверный as_of
и valid_until ближайшей границы акции. Пассивный SQL revision не используется
для кеширования цен: повторный preview всегда читает текущие значения.
Смысл активной акции задаёт Domain Catalog
(начало включительно, конец исключительно), цена VARIABLE не подставляется.
Feed Application получает снимок через собственный порт и Infrastructure-адаптер;
чужой ORM/Domain не проникает в Feed Domain/Application.

Read-only Query PreviewFieldCalculation читает Feed schema projection без
Feed.restore, проверяет expected_version/архив, собирает временное определение
поля и вызывает Domain. Клиент передаёт только ID и optional definition_override;
цен/часов клиента во входе нет. Preview не пишет БД и не увеличивает Feed.version.
HTTP и Console описаны в 12.1.2 и 13.2; SQL-схема не меняется.

Готовность проверена Domain/Application/HTTP/PostgreSQL тестами: IF/ELSE и short
circuit, типы всех ветвей, числовая точность/лимиты, вариант и принадлежность,
действие акции/ноль, валютная метка, версии/архив/tenant/права/CSRF, сохранение AST.
Console проверяется mapper/state/race тестами и браузером с реальным API:
несохранённый ввод, save/reload, простой товар/вариант, desktop/mobile.
Параметры Catalog `price.purchase` и `product.category_ids` подключены в срезе
16.6.2. Фоновое обновление и публичная ссылка описаны в 16.7.

### **16.6. Publication и проекции**

#### **16.6.1. Сохранённый ассортимент — реализовано**

Законченный сценарий: открыть «Товары» → выбрать SIMPLE/конкретные VARIANT →
сохранить атомарный пакет → открыть повторно → проверить цену → приостановить/
возобновить → убрать в архив → явно вернуть с прежним ID.
Domain добавил версию и поведение участия; Infrastructure — модель/миграцию,
write/query repositories и адаптер публичного batch-reader Catalog; Application —
конкретные сценарии; HTTP — самостоятельные методы; Console — список/диалог/
карточку/действия и существующий preview цены. Публикации не вложены в Feed.
Нет дублей, не стираются overrides, новые варианты не включаются автоматически.
Все изменения состава сериализуются с архивом Feed и защищены версиями.

#### **16.6.2. Полный расчёт публикации, предпросмотр и пробный CSV — реализовано**

Пакетный снимок Catalog передаёт эффективный контент по локалям, категории и
`purchase_price`. Параметры `price.purchase` и `product.category_ids` доступны
в формулах и серверных метаданных. `FieldValueResolver` и `PublicationResolver`
разрешают STRING/TEXT/MONEY, применяют fallback, преобразования, ограничения и
сохранённые overrides. Console показывает до 20 ENABLED-публикаций. Пробный CSV
обрабатывает весь включённый ассортимент тем же resolver.

Сохранённые схемы с устаревшим `purchase_source: null` читаются и при сохранении
переходят к целевому формату. Заполненная устаревшая привязка требует явного
перехода формулы на закупочную цену Catalog.

#### **16.6.3. Управление overrides и постоянные проекции**

Set/ResetOverride и редактор значений публикации реализуют ручной ввод с
проверкой схемы. При добавлении материализованных проекций использовать
версии Feed и публикации, зависимости
Catalog, valid_until и условный upsert. Ревизия выбранной позиции должна меняться
при записи `purchase_price` через редактирование или импорт. Эти работы можно
выполнить после фоновой генерации из 16.7.

### **16.7. Публичный CSV на хосте tenant**

Сценарий завершён, когда пользователь нажимает «Обновить фид» в Console,
видит отчёт, копирует ссылку и скачивает CSV с хоста своего tenant. Срез
использует `PUBLIC` и `STRICT`. `SKIP_INVALID`, XML и PRIVATE с `FeedAccessKey`
подключаются в 16.8.

1. **Domain и хранение.** Заменить `FeedGeneration` и `FeedArtifact` агрегатом
   `FeedExportState`. В tenant-миграции добавить `fb_export_states` с `feed_id`
   как первичным ключом и FK к Feed. В одной строке хранить текущую задачу,
   последний отчёт и `active_file_id`. Для постраничного чтения хранить
   диагностики последнего отчёта в `fb_export_issues`. `active_file_id` указывает
   на `StoredFile` по контракту Files. Добавить `public_link_id` и метод
   ротации в Feed. Сохранить совместимость существующих Feed, схем и публикаций.
2. **Постановка.** Реализовать `POST /feeds/{id}/export/refresh`. После
   проверки версии, прав и выбранного формата CSV сохранить снимок схемы
   и настроек из БД. В той же транзакции поставить `feed_builder.generation.run`
   в существующий `scheduled_jobs`. Повтор запроса при активной задаче
   возвращает её состояние. Аренду задания и технические повторы ведёт общий
   `jobs worker`.
3. **Сборка и отчёт.** Зарегистрировать handler в существующем dispatcher.
   Обработать все ENABLED-публикации пакетами через `PublicationResolver`.
   Посчитать позиции без замечаний, с предупреждениями и с блокирующими
   ошибками. В `STRICT` предупреждения допускаются, а блокирующая ошибка
   отклоняет весь новый CSV. При успехе сохранить CSV через Files, чтобы он
   появился в Storage. В одной транзакции зафиксировать новый `active_file_id`
   и последний отчёт. При отклонении или окончательном сбое сохранить отчёт
   и прежний активный файл. После успешной замены поставить прежний файл
   на очистку через Files с проверкой использования.
4. **Публичный HTTP.** Добавить маршрут Feed Builder на существующем хосте
   tenant по адресу `https://<tenant-host>/api/public/feed-builder/{public_link_id}/feed.csv`.
   Использовать существующее проксирование `/api/` и определять tenant по
   доверенному хосту. Выдавать активный файл через Files как CSV-вложение
   без сессии и токена. Создавать адрес при первой успешной сборке. Обычная
   пересборка сохраняет URL, а авторизованная ротация в Console API меняет
   `public_link_id` и закрывает прежний адрес.
5. **Console.** Добавить экран «Экспорт» с запуском, статусом, датами
   активного файла и последнего отчёта, диагностикой, кнопками копирования
   и замены ссылки. Использовать отдельные типизированные API, query и
   mutation для экспорта. Кеш привязан к tenant и Feed, опрос прекращается
   при завершении задачи и уходе со страницы.

Готовность проверяется на фиде с более чем 20 публикациями. Если блокирующих
ошибок нет, CSV содержит все включённые позиции, в том числе позиции с
предупреждениями. Файл виден в Storage и скачивается без входа по адресу
tenant. Повторная успешная сборка меняет содержимое по тому же адресу.
Блокирующая ошибка в `STRICT` обновляет отчёт и сохраняет прежний CSV. Если
первая сборка отклонена, ссылка ещё не появляется. После ротации работает
новый адрес. Старый адрес и тот же путь на другом tenant-хосте возвращают
404. Сценарии конкуренции и восстановления проверяются по разделам 15.3–15.5.

### **16.8. Дополнительные форматы, политика проверки и приватный доступ**

- Реализован Generic XML. Воркер выбирает сериализатор
  по снимку задачи. Файл открывается по публичной ссылке `feed.xml` на хосте
  tenant. После смены настроек прежний формат и его ссылка доступны до
  успешной пересборки.
- Реализован `SKIP_INVALID` для CSV и XML. Политика выбирается в Console.
  Отчёт частичной публикации показывает число записей в файле и число
  пропущенных позиций, с диагностикой по каждой ошибочной позиции. При
  отклонении всех включённых позиций или техническом сбое сохраняется текущий файл.
- Добавить PRIVATE и операции `FeedAccessKey`. Несколько токенов одного
  фида выпускаются и отзываются независимо. Токен принимается в
  `?token=…`, проверяется до кеша и исключается из логов.

### **16.9. Stabilization**

Integration/E2E/нагрузка/security, конкуренция, AST limits, права/derived data,
время акций, смена формулы с пользовательским курсом во время запуска, восстановление задач/cleanup,
мобильный/доступный UI, observability и весь архитектурный перечень.

Готовность: критерии раздела 18 и соответствующие проверки выполнены;
нет известных нарушений слоёв/контрактов/изоляции. Пресеты — отдельное расширение.

## **17. Расширения после MVP**

| Возможность | Подготовленный механизм |
| --- | --- |
| Черновики схемы, история ревизий и публикация выбранной версии | Отдельные хранилища `fb_schema_drafts` и `fb_schema_versions`, указатель `active_schema_version` и команда `PublishFeedSchema` |
| Пресеты Prom/Rozetka/пользовательские | Исходные определения полей и AST с новыми ID при применении |
| Специфические форматы площадок | Отдельные FormatProfile/Serializer по актуальным официальным контрактам |
| Категории поддерева | Явная операция + snapshot дерева от владельца, без скрытых предков |
| Другие параметры/характеристики/бренд | ParameterRegistry с типами/правами и публичный owner reader |
| Межполевые выражения | Отдельный граф зависимостей и проверка циклов до расчёта |
| Вложенные объекты/массивы/изображения | kind/children/item_schema, media types |
| Группировка вариантов и представление семейств | Новые значения FeedProductMode, явные правила родительских записей/групповых ID и профили форматов |
| AI/переводы | ai_instruction + locale, отдельный suggestion use case |
| Динамический ассортимент | SelectionPolicy и соответствующий Application Engine |
| Расписание/событийная перегенерация | Вызов RequestFeedRefresh внешним планировщиком |
| Bulk overrides | Отдельный Application сценарий с optimistic locking |
| Строгий snapshot всего источника | Согласованные immutable source snapshots, не только revision ledger |
| Миграция смысла поля | Явный перенос несовместимых overrides с preview/проверками |
| Совместное использование правил вне Feed | Новый явный публичный контракт, если появится такой сценарий |

Плоская выгрузка простых товаров/выбранных вариантов в VARIABLE_TO_SINGLE,
условия по категориям, арифметика с ценами Catalog и явный пересчёт пользовательской
формулой входят в целевой MVP.
Предустановка пресета не делает поля особыми и не связывает изменение одного
Feed с другим. Схема, публикация и итоговый артефакт сохраняют отдельный смысл.

## **18. Критерии готовности**

### **18.1. Непосредственный первый срез**

1. Создаётся Feed с пустой или явно переданной пользовательской схемой.
2. Нет встроенных полей по именам и привилегированных ролей.
   Export Settings содержит единственный FeedProductMode.VARIABLE_TO_SINGLE
   по умолчанию и обязательное format_settings с одним CSV либо XML VO.
   Feed.create требует export_settings. Фабрики сохраняют режим и параметры,
   VO отклоняет коллекции/нетипизированные значения; формат определяется классом VO.
3. FieldDefinition/ConditionalPriceRule имеют только create/restore;
   Feed дополнительно получил change_settings/archive в срезе 18.1.2.
   VO/enums/ошибки корректно разнесены, каждый VO — отдельный файл.
   Настройки принадлежат трём VO типов, структура расчёта проверяется
   PriceCalculationStructurePolicy без исполнения формул; уникальность — фабрикой Feed.
4. Условия, формулы, источники и настройки представлены типизированными
   неизменяемыми объектами. Неизвестный тип/некорректная структура отклоняются.
   Прямые источники ограничены SourceProvider.CATALOG и четырьмя CatalogSourcePath;
   произвольные строки и чужие Enum не принимаются.
5. Restore сохраняет идентичность, порядок и настройки без генерации новых данных.
6. Срез ограничен Domain-объектами и структурными проверками.
   Unit-тесты Domain не требуют БД или HTTP; Feed CRUD имеет отдельные проверки.

#### **18.1.1. Предыдущий объектный срез**

`FeedPublication`, `FeedGeneration`, `FeedArtifact` и `FeedAccessKey`
получили create/restore и тесты инвариантов. `FeedPublication` дополнительно
получил поведение в последующих срезах. Критерии замены `FeedGeneration`
на `FeedExportState` заданы в 15.1.1 и 16.7.

#### **18.1.2. Реализованный первый Feed CRUD**

1. POST создаёт DRAFT с пустой схемой, одним обязательным форматом и version=1.
2. Список/карточка читают проекции, список по умолчанию исключает архив.
3. PATCH атомарно изменяет только настройки с expected_version, сохраняя схему;
   no-op сохраняет версию/дату. Некорректные/устаревшие изменения отклоняются.
4. DELETE архивирует и возвращает 204; код и строка остаются, повтор идемпотентен.
5. Репозитории, mapper, модель и tenant-миграция проверены на PostgreSQL:
   изоляция tenant, уникальность, CAS/конкуренция, rollback, Decimal/AST round-trip.
6. Аутентификация, авторизация и CSRF подключены через существующие контракты.
7. Feed получил CRUD, FeedPublication — внешний срез состава 18.1.6;
   ревизии/генератор и внешние методы AccessKey появятся отдельно. Console CRUD описан в 18.1.3.

#### **18.1.3. Реализованный интерфейс Console**

1. «Фиды» доступны в навигации: список, поиск, статусы, страницы и фильтр архива.
2. Создание пустого Feed и редактирование настроек используют один явный CSV/XML,
   VARIABLE_TO_SINGLE, STRICT и UTF-8 через существующий API с CSRF.
3. Архивация подтверждается; архив открывается только для просмотра, код занят.
4. Конфликты и refetch сохраняют ввод; повторный pending/неоднозначный POST
   не создаёт скрытые дубликаты, tenant/session state не смешивается.
5. Генерация и доступ пока не представлены как готовые UI-функции.
   Управление составом через FeedPublication реализовано в 18.1.6.
   Конструктор схемы и формулы добавлены следующими срезами 18.1.4–18.1.5.

#### **18.1.4. Реализованный конструктор рабочей схемы**

1. Схема создаётся пользователем из равноправных полей и сохраняется полным снимком.
2. Настройки типов структурированы; источники закрыты Enum/реестром, локали
   проверяются справочником, currency необязательна и не конвертирует сумму.
3. ID/порядок/параметры/Decimal-строки/существующий AST/AI сохраняются без потерь.
4. Shared Feed.version защищает схему, настройки и архив от потери изменений;
   ошибка не оставляет частичной записи, no-op не увеличивает версию.
5. Console поддерживает полный цикл редактирования и повторного открытия,
   конфликты/dirty/pending/tenant/session/read-only архив и доступную навигацию.
6. Сохранённое определение является актуальной схемой Feed. Формулы и тестовый
   выбор товара для расчёта добавлены срезом 18.1.5, ассортимент — 18.1.6.

#### **18.1.5. Реализованные формулы и предпросмотр цены**

1. MONEY/CALCULATED сохраняет ELSE и упорядоченные IF с устойчивыми rule IDs.
2. Единая Domain Policy проверяет новые/изменённые формулы при save и preview;
   вычислитель возвращает Decimal-сумму с необязательной валютной меткой.
3. Preview работает с текущим вводом поля и реальными Catalog SIMPLE/VARIANT,
   возвращает ветвь, параметры, шаги/issues и фактические версии/временной контекст.
4. Preview не изменяет Feed, не создаёт публикаций и не запускает сборку файла.
5. Console поддерживает визуальное дерево, быстрые наценки, выбор конкретного
   варианта, сохранение/reload и отмену поздних результатов при ABA/смене контекста.
6. Изменение определения/товара/версии и граница акции делают результат устаревшим;
   смена tenant/session очищает результат и выбор. 409 сохраняет черновик.
7. Закупочная цена Catalog и категории подключены в следующем срезе 18.1.7.

#### **18.1.6. Реализованное управление ассортиментом**

1. Простые товары и выбранные варианты сохраняются отдельными FeedPublication.
2. Пакет до 100 атомарен, повтор/конкуренция сохраняют ID/status/overrides.
3. Пауза/возобновление/архивация/явный возврат выполняются через корень и CAS.
4. Конструктор схемы/формулы и Feed.version от изменения состава не меняются.
5. Console поддерживает URL/reload, серверный поиск/пагинацию, выбор между
   страницами, фиксированный снимок вариантов, 409/pending/контекст и mobile.
6. Проверка цены использует сохранённую схему и существующий evaluator без записи.
7. Архив Feed read-only, удалённый источник виден как недоступный без потери связи.
8. Полный расчёт и пробный CSV описаны в 18.1.7.

#### **18.1.7. Реализованный расчёт публикаций и пробный CSV**

1. Один resolver рассчитывает STRING/TEXT/MONEY по сохранённой схеме и снимкам
   Catalog. Предпросмотр показывает до 20 ENABLED-публикаций и ошибки по полям.
2. Пробный CSV содержит весь ENABLED-ассортимент в том же порядке. При одинаковых
   входах значения первых 20 совпадают с предпросмотром.
3. Блокирующая ошибка любой включённой позиции прерывает скачивание, в том числе
   за пределами первых 20.

### **18.2. Полный целевой MVP после последующих срезов**

1. Пользователь создаёт пустой Feed и сам задаёт поля/порядок/экспорт.
2. Текстовые поля имеют независимые locale/fallback, MONEY — необязательные валютные метки результата.
3. В MONEY выбираются source/manual/calculated, необязательная валютная метка, ELSE и
   упорядоченные IF-правила категории/других зарегистрированных параметров.
4. Формулы используют `price.regular`, `price.sale`, `price.effective` и
   `price.purchase` из Catalog. Закупочная цена читается у выбранного SIMPLE
   или VARIANT с проверкой tenant и прав. `null` означает отсутствие цены,
   `0` участвует в вычислении как значение.
5. Preview показывает первую совпавшую ветвь/ELSE, разрешённые данные и errors
   по field/rule/path. Нет скрытой подстановки отсутствия нулём/другой ценой.
6. Приоритет manual исключает повторную наценку/формулу; reset возвращает
   автоматическое определение, остальные поля не затрагиваются.
7. Сохранённые схема и настройки Feed задают следующую генерацию. Запуск
   фиксирует их снимок. Публичная выдача переключается после успешной активации.
8. Привязка простых товаров и выбранных вариантов идемпотентна по паре ID;
   выбор только белого топика даёт одну публикацию, родитель и остальные варианты
   не экспортируются. Новые варианты не подключаются автоматически. Проекции
   учитывают версии формул, время акции и ревизии использованных данных Catalog,
   в том числе изменение `purchase_price` выбранной позиции. Устаревание видно
   пользователю.
9. После устранения blocking issues ENABLED-позиции готовы; задача `scheduled_jobs`
   запускает генерацию одного Generic CSV либо XML из staging с фиксированным format_settings,
   product_mode/as_of/engine version и числовыми константами формулы. VARIABLE_TO_SINGLE даёт по одной
   самостоятельной записи на публикацию, без строки VARIABLE и группировки;
   схема полей общая для SIMPLE/VARIANT.
10. Предпросмотр и экспорт дают одинаковую цену при одинаковых данных Catalog,
    схеме, overrides и as_of. Catalog сохраняет исходные цены позиции.
11. Один `FeedExportState` на Feed хранит текущую задачу, последний отчёт
    и один `active_file_id`. Активация сверяет снимок с сохранёнными настройками
    и проверяет актуальность задачи.
12. При отказе отчёт обновляется, а прежний файл остаётся доступен. После
    успешной замены прежний файл очищается. Повторы сохраняют снимок и as_of.
13. Публичный URL отдаёт текущий файл с хоста tenant. Старый адрес после
    замены и чужой tenant не получают файл. Права защищают исходные параметры
    и trace. Механика приватных ключей описана отдельным шагом 16.8.
14. Пройдены Domain/Integration/E2E/нагрузочные и frontend проверки, архитектурный
    перечень и stabilization. Пресеты и площадочные профили остаются будущими срезами.

**Итоговый поток:**

```text
Выбранные SIMPLE/VARIANT Catalog с их ценами и нужным контекстом родителей
  + числовые параметры формулы + as_of
  → снимок сохранённых Feed.schema и Feed.export_settings в FeedExportState + scheduled_job
  → jobs worker → ExecuteFeedRefresh
  → VARIABLE_TO_SINGLE, общие поля и AST денежного расчёта
  → FeedPublication override либо IF/ELSE/expression
  → transforms / Decimal rounding / constraints
  → ResolvedPublication
  → одна плоская ExportRecord на публикацию + FormatProfile + staging
  → один файл Files / Storage
  → активный file_id и последний отчёт в FeedExportState
  → HTTP Feed Builder на хосте tenant
```

Domain моделирует и проверяет бизнес-смысл; Application получает входы и
координирует процессы; Infrastructure хранит/читает/сериализует; Presentation
предоставляет API и конструктор. Первый шаг — только правильные Domain-объекты
Feed, а не реализация всего описанного жизненного цикла сразу.
