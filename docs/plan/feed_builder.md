# **FeedBuilder — финальный целевой план реализации**

**Архитектура:** DDD + Clean Architecture\
**Backend:** Python, FastAPI, SQLAlchemy Async, PostgreSQL\
**Frontend:** Vue 3, TypeScript, TanStack Vue Query\
**Определения:** версионируемые JSONB-схемы с типизированными условиями и AST\
**Целевой MVP:** один выбранный Generic CSV либо XML на Feed, плоская выгрузка простых товаров и выбранных вариантов, расчёт денежных полей внутри Feed

Документ фиксирует согласованную целевую модель и последовательность реализации.
Все поля пользовательские и равноправные; обычный Feed начинается с пустой схемы.
Наценки/условия/формулы находятся в определении конкретного денежного поля.
Денежные значения FeedBuilder — точные числовые суммы. Необязательный код валюты
принадлежит полю и служит меткой результата; он не выполняет конвертацию.
Курс пользователь задаёт обычной константой своей формулы. Курсовых сервисов,
автоматического наследования валюты источника и FX-контекста модуль не использует.
Реализованы объекты Domain Feed/Publication/Generation/AccessKey и первая
рабочая вертикаль Feed CRUD: изменение общих настроек, архивация, PostgreSQL,
Application и Console API/UI. Добавлен конструктор рабочей схемы с полями,
источниками, настройками типов и атомарным сохранением. Остальные три агрегата
остаются объектными. Ревизии, публикация схем, вычисление значений, генерации
и управление секретами пока не реализованы. Будущие разделы описывают цель.

## **1. Цель, границы и порядок реализации**

FeedBuilder — самостоятельный bounded context, создающий пользовательские
выгрузки из Catalog и других разрешённых источников. Условия и формулы цены
принадлежат денежному полю конкретной схемы Feed. Отдельный модуль прайс-листов
или наценок для работы FeedBuilder не требуется.

### **1.1. Целевые возможности MVP**

1. Создать Feed с названием, кодом, явно выбранным CSV либо XML и пустой пользовательской схемой.
2. Собрать структуру предложения из произвольного числа STRING, TEXT и MONEY полей.
3. Выбрать каждому полю источник или ручное заполнение, язык/валюту,
   ограничения, преобразования и экспортное имя.
4. Для MONEY выбрать прямой источник либо условный расчёт с формулой по умолчанию.
5. Задать IF/ELSE IF правила по категориям и другим зарегистрированным параметрам
   товара, используя обычную, акционную и явно определённую закупочную цену.
6. Привязать простые товары и выбранные варианты Catalog, просматривать значения/ошибки
   и задавать независимые overrides каждой позиции.
7. Сохранять draft, публиковать неизменяемую версию схемы и проверять preview.
8. Асинхронно генерировать один Generic CSV либо XML из проверенного набора записей.
9. Получать файлы по постоянным HTTPS-ссылкам; ошибочная генерация сохраняет прежнюю выдачу.

| Тип поля | Значение | Контекст |
| --- | --- | --- |
| STRING | str | Локализованный или языконезависимый текст |
| TEXT | str | Описание и длинный текст |
| MONEY | PriceAmountVO с Decimal; PriceValueVO для будущего результата | Необязательная валютная метка поля, источник или формула |

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

- Пустая схема корректна для создания Feed и рабочего draft.
- constraints.required требует значения в публикации, а не наличия поля
  с определённым именем во всех Feed.
- field_id — стабильная идентичность поля; переименование key/label/export.name
  и перестановка не создают новое поле.
- Состав произволен в пределах поддерживаемых типов и структурных ограничений.
- Для публикации Generic CSV/XML требуется хотя бы одно экспортируемое поле;
  конкретных обязательных ключей нет.
- После публикации нельзя менять смысл того же field_id несовместимым типом,
  либо локалью: создаётся новое поле либо отдельная будущая миграция.
  Необязательную валютную метку можно менять без смены field_id и пересчёта суммы.
  Это правило одинаково для всех полей. Формулы и constraints могут изменяться
  новой версией схемы при сохранении идентичности и совместимого типа поля.

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

#### **1.3.1. Предыдущий объектный срез: Publication, Generation и AccessKey**

После объектов Feed добавлены три самостоятельных Aggregate Root:
FeedPublication, FeedGeneration и FeedAccessKey. Их фабрики create/restore
проверяют только значения и согласованность сохранённого состояния.
FeedArtifact — зависимая Entity генерации; каждый VO находится в своём файле.

Ревизии, отдельный контейнер схем и методы изменения объектов не создаются.
Генерация хранит полный GenerationDefinitionSnapshotVO текущих FeedSchemaVO и
FeedExportSettingsVO; ссылки schema_revision_id/schema_version/activation_id
не нужны для конструирования. Положительный request_sequence обозначает порядок
запросов сборки, а не версию схемы; атомарное выделение появится с хранением.

Feed остаётся в существующем контракте. Коллекции публикаций, генераций и ключей
в него не добавляются. Ключи имеют самостоятельный жизненный цикл и ссылаются
на Feed по ID. Нет evaluator, публикации схем, запуска/повтора сборки,
выпуска/отзыва секретов, событий, repositories, SQL, Application, API или UI.
Исторические версии/draft в следующих разделах — отложенное поведение,
которое потребуется отдельно согласовать перед реализацией.

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

Текущий draft — единственная рабочая схема Feed. У неё нет собственной версии,
таблицы, commit name/description, истории или ссылок на опубликованную схему.
Feed.version общий для схемы, настроек и архивации. Реализованы чистый evaluator,
редактирование IF/ELSE и предпросмотр MONEY на реальном SIMPLE/выбранном VARIANT.
Публикация схем, участие товаров в Feed и генерация остаются будущими.
API сохраняет полный существующий AST. Определения с пока неподключёнными закупкой/
категориями сохраняются без изменений и доступны в Console только для просмотра.

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
Полное разрешение полей, редактор overrides и материализованные проекции —
следующая часть среза 16.6; текущая проверка цены не означает READY всего предложения.

### **1.4. Границы контекстов**

```text
Catalog: простые товары, родители/варианты, эффективный контент, regular/sale price, категории и ревизии
Supplier Sourcing: явно выбранное закупочное предложение
reference_data: поддерживаемые локали; форма валютной метки проверяется CurrencyVO
        ↓ публичные Application Ports
FeedBuilder: схема → условный расчёт поля / override → проекция
        ↓
ExportRecord staging → Generic CSV / Generic XML → публичные артефакты
```

FeedBuilder не изменяет Catalog и Supplier Sourcing, не импортирует их ORM
или внутренние агрегаты и не реализует Channels/API-синхронизацию площадок.
Исходные данные получает Application, а чистый Domain-вычислитель работает
с immutable snapshots. Channels не обязан использовать внутренние правила Feed;
согласование API-цен с выгрузками — отдельный будущий контракт.

Закупочная цена не является однозначным свойством Catalog: в проекте она есть
в предложениях Supplier Sourcing. Для её использования требуется конкретное
предложение или явное правило выбора в конфигурации источника. Минимальная цена
предложения и себестоимость складского остатка не смешиваются автоматически.

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
| Корни агрегатов целевого модуля | Feed, FeedPublication, FeedGeneration, FeedAccessKey |
| Что хранит Feed | Общую пользовательскую схему предложений и настройки экспорта |
| Product Mode MVP | Только VARIABLE_TO_SINGLE, по умолчанию в export_settings |
| Состав выгрузки | Явно выбранные простые товары и конкретные варианты через FeedPublication |
| Представление вариантов | Одна самостоятельная запись на выбранный вариант, без строки родителя и группировки |
| Где определены наценки | В MoneyValueDefinitionVO конкретного MONEY-поля |
| Где хранятся правила | В definition версии FeedSchema, JSONB |
| Как выбирается правило | Первое совпадение в порядке массива; иначе default_expression |
| Что возвращает формула | Конечную денежную сумму до округления/constraints |
| Как представлены выражения | Типизированное декларативное дерево, не исполняемый текст |
| Где хранится ручное значение | Override публикации по field_id |
| Какая версия включает изменение формулы | Новая версия схемы, без отдельной версии политики |
| Как создаётся файл | Один явно выбранный CSV либо XML на Feed; одна генерация — один артефакт |
| Что сохраняется при ошибке | Предыдущая успешная активная генерация |
| С чего начинается реализация | Только Domain-объекты Feed с create/restore |

### **2.1. Definition, Override и Resolved Value**

Definition — описание поля для всей версии схемы: тип, источник/расчёт, язык,
валюта, условия, выражения, fallback, constraints, transforms и экспорт.
Override — индивидуальное значение конкретной публикации без копии остальных
данных товара. Resolved Value — итог после автоматического определения либо
ручного ввода, округления и проверки. Эти модели не подменяют друг друга.

### **2.2. Архитектурный перечень для проверки всего diff**

Нормативные документы: [backend](../architecture/backend.md) и
[frontend](../architecture/frontend.md). Требования проверяются по объёму среза:

1. Структура: модуль → слой → Aggregate Root → ответственность. Дочерние Entity
   поля/правила/артефакт не получают самостоятельных repositories. Текущий срез
   содержит Domain четырёх корней и application/infrastructure/presentation только
   для Feed CRUD и рабочей схемы; общая модель хранения расположена в infrastructure/persistence/models.
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
8. Application получает данные Catalog, категорий, закупочных источников
   и справочников через порты; Domain не импортирует чужие агрегаты.
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
  domain/{feed,publication,generation,access_key}/
  application/{feed,publication,generation,access_key}/
    command/<scenario>/{command.py,handler.py,dto.py}
    query/<scenario>/{query.py,handler.py,dto.py}
    port/
  application/service/
  infrastructure/{feed,publication,generation,access_key}/persistence/
  infrastructure/persistence/models/<table>.py
  infrastructure/{catalog,supplier_sourcing,storage,serialization}/
  presentation/{feed,publication,generation,access_key}/
    router.py, depends.py
    http/{controller,request,response}/<scenario>.py
  presentation/depends/
```

Объектный срез создаёт Domain из разделов 3.4 и 3.7–3.10.
Текущая вертикаль Feed добавляет необходимые файлы четырёх слоёв по разделу 1.3.2;
пустые заготовки сценариев Publication/Generation/AccessKey не создаются.
Остальные каталоги появляются по факту реализации. Общие UoW/jobs/events/storage
механизмы переиспользуются; файловая структура не определяет границы агрегатов.

## **3. Domain: текущие объекты и будущие границы**

### **3.1. Aggregate Roots целевого модуля**

| Корень | Ответственность | Когда реализуется |
| --- | --- | --- |
| Feed | Определения полей и общие настройки | Объекты, change_settings/change_schema/archive, CRUD и редактор рабочей схемы реализованы; активация — позже |
| FeedPublication | Привязка позиции, участие, индивидуальные overrides | Объекты и проверки — текущий срез; поведение — позже |
| FeedGeneration | Снимок определения, состояние сборки, контекст и один артефакт | Объекты и проверки — текущий срез; выполнение — позже |
| FeedAccessKey | Состояние отдельного ключа чтения публичного файла | Объекты и проверки — текущий срез; выпуск/отзыв — позже |

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
validation_policy=STRICT. ExportFormatSettings — закрытое объединение
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
No-op не пишет БД. Архив и время ранее updated_at отклоняются. Публикация схемы
и генерация остаются будущими; отдельного CRUD внутренних Entity нет.
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

PriceCalculationVO содержит упорядоченный
`tuple[ConditionalPriceRule, ...]`, обязательное default_expression и
purchase_source: PurchasePriceSourceVO | None. При зависимости price.purchase
источник закупки обязателен; в остальных расчётах он отсутствует.
Пустой список правил допустим: тогда всегда используется default_expression.
PurchasePriceSourceVO — отдельная закупочная привязка, не SourceReferenceVO.
Её provider/path в JSON-примере раздела 4 описывают binding закупки и не добавляют
supplier_sourcing в SourceProvider прямых источников поля.
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
    purchase_price_source.py         PurchasePriceSourceVO
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
PriceCalculationStructurePolicy остаётся чистой Domain Policy: проверяет ID правил,
глубину/число узлов и соответствие purchase_source зависимостям. Её вызывает
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

### **3.6. Состояние Feed в последующих срезах**

Сейчас schema уже является единственным рабочим определением. При отдельном
согласовании публикации и ревизий добавятся ссылка на текущую неизменяемую опубликованную
версию, draft revision/base version, configuration_version,
счётчик запросов и ссылка на активную генерацию вместе с её sequence.
Структура FieldDefinition и PriceCalculationVO при этом сохраняется.
История схем целиком не загружается в агрегат.

Будущие domain-операции владеют изменениями полей/правил и публикацией;
ни Application, ни дочерний объект не обходят корень. Конкретные методы
добавляются вместе с поведением соответствующего среза, не заготовками сейчас.
FeedGeneration/FeedPublication/FeedAccessKey имеют собственные create/restore.
FeedPublication дополнительно получил поведение участия в срезе 16.6.1;
поведение Generation/AccessKey появится отдельно. row_version не означает commit Domain.

Будущий жизненный цикл публикации схемы переводит Feed из DRAFT в ACTIVE;
добавление FeedPublication такого перехода не выполняет.
ACTIVE можно приостановить и затем возобновить через PAUSED. Новая публикация
у PAUSED не возобновляет генерации автоматически. ARCHIVED — конечное состояние,
из него редактирование/генерация не разрешены. Пауза сохраняет прежнюю публичную
выдачу, архивация отключает public route в общей транзакции и сохраняет историю.
UpdateFeedSettings передаёт желаемый status, переход проверяет Domain.

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

### **3.8. FeedGeneration без ревизий схем**

| Поле | Тип / смысл |
| --- | --- |
| id, feed_id | FeedGenerationIdVO, FeedIdVO |
| request_sequence | GenerationSequenceVO: положительное целое, не версия схемы |
| definition_snapshot | GenerationDefinitionSnapshotVO |
| status | GenerationStatus: PENDING / RUNNING / SUCCEEDED / FAILED |
| calculation_context | GenerationCalculationContextVO или None до фиксации |
| attempt_count | Неотрицательное целое, bool не допускается |
| current_attempt | GenerationAttemptVO только для RUNNING |
| counts | GenerationCountsVO |
| failure | GenerationFailureVO только для FAILED |
| artifact | FeedArtifact только для SUCCEEDED |
| requested_at, started_at, finished_at | Timezone-aware даты, начало/завершение могут отсутствовать |

GenerationDefinitionSnapshotVO хранит schema: FeedSchemaVO,
export_settings: FeedExportSettingsVO и
calculation_engine_version: CalculationEngineVersionVO.
Engine version — положительная версия семантики интерпретатора, не ревизия схемы
и не отдельная ценовая политика. Снимок содержит VARIABLE_TO_SINGLE и один
обязательный format_settings CSV либо XML. Менять его текущими настройками Feed
при повторе нельзя. Поля/AST проверяются FeedSchemaStructurePolicy из фабрики
генерации: одинаковые правила состава применяются и в Feed.restore, без
создания временного Feed и без переноса инвариантов в VO или mapper.

create требует identifier/feed_id/request_sequence/definition_snapshot/now
и создаёт PENDING: attempt_count=0, нулевые counts, остальные результаты None.
Пустая схема допустима как снимок объекта; разрешение фактического запуска
относится к будущему поведению, а не к конструированию.

restore проверяет согласованность:

- PENDING не содержит начатой работы, контекста, попытки, ошибки или файла.
- RUNNING требует started_at и current_attempt; finished_at/итоговый файл/ошибка
  отсутствуют. Номер текущей попытки равен attempt_count.
- SUCCEEDED требует started_at/finished_at, расчётный контекст, полный учёт
  позиций и один артефакт. При STRICT rejected_items=0.
- FAILED требует finished_at и failure, не содержит current_attempt или
  итогового артефакта. Допустим сбой до первого захвата и частичный прогресс.
- attempt_count > 0 соответствует наличию started_at. Даты выполнения не раньше
  requested_at; завершение не раньше начала. as_of находится в интервале выполнения.
- Учтённые позиции не превышают total_items; до расчёта позиций нужен контекст.
  До первой попытки все counts нулевые.
- Формат и MIME артефакта соответствуют снимку; время файла находится между
  началом и завершением. Вложенная Entity повторно проверяется через restore.

GenerationAttemptVO: number, GenerationAttemptTokenVO, claimed_at, lease_until.
Номер положительный, lease_until > claimed_at, claimed_at не раньше started_at.
started_at сохраняет начало первой попытки, а не заменяется временем retry.
Восстановление истёкшего lease допустимо: Domain не обращается к текущим часам.
В завершённых состояниях current_attempt=None, число попыток сохраняется.

GenerationCalculationContextVO содержит только as_of для временных условий
и повторных попыток. Курсы, снимки котировок и валютный контекст отсутствуют.
Пользовательский курс — DecimalLiteralVO в схеме, поэтому зафиксирован
в GenerationDefinitionSnapshotVO вместе с остальными параметрами формулы.
Фиксация времени и retry появятся в следующих срезах.

GenerationCountsVO содержит total_items, exported_items и rejected_items.
exported_items — подготовленные корректные экспортные записи, включая staging;
это не доказательство публичной выдачи файла. FAILED может сохранить частичный
прогресс. GenerationFailureVO содержит стабильный code в lower_snake_case
до 100 символов и безопасный message до 1000 символов без управляющих знаков.
Очистка внешних исключений — ответственность вызывающего слоя.

FeedArtifact — Entity внутри FeedGeneration с create/restore:
FeedArtifactIdVO, ExportFormat, ArtifactStorageKeyVO (до 1024 символов),
ArtifactContentTypeVO (text/csv либо application/xml без параметров),
ArtifactChecksumVO (64 lowercase hex символа SHA-256), неотрицательный
size_bytes и created_at. В ней нет содержимого файла, публичного URL или I/O.
Формат и базовый MIME согласованы; нулевой размер допустим.
Подробные issues по всем публикациям и staging не являются коллекциями агрегата.

Успех генерации и активация — разные действия. Изменившаяся схема/конфигурация
или более новая активная sequence препятствуют активации старого результата.
Повтор использует прежние as_of/схему и константы формулы, новая конфигурация требует нового задания.
Методы переходов, выделение sequence, fencing/heartbeat, активация и сравнение
конфигураций появятся отдельным срезом; сейчас эти процессы не исполняются.

### **3.9. FeedAccessKey**

Самостоятельный Aggregate Root: id: FeedAccessKeyIdVO, feed_id: FeedIdVO,
token_hash: AccessTokenHashVO, status: AccessKeyStatus, created_at, revoked_at.
Feed не хранит коллекцию ключей. Ключ предназначен только для чтения публичного
файла одного фида, не для управления Feed или запуска сборки.

AccessKeyStatus: ACTIVE / REVOKED. create принимает готовые ID/digest/now,
создаёт ACTIVE с revoked_at=None. restore сохраняет все поля; ACTIVE запрещает
revoked_at, REVOKED требует timezone-aware дату не раньше created_at.
AccessTokenHashVO содержит только immutable bytes длиной 32 (SHA-256 digest);
значение исключено из repr. Секрет не хранится и не восстанавливается.
Генерация секрета, хеширование и проверка находятся за пределами Domain-среза.
Будущая ротация атомарно создаёт новый ключ и отзывает старый, а не меняет digest
существующего. Публичный tenant route registry остаётся Infrastructure/read-side.

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

Общий FeedBuilderDomainError объединяет ошибки четырёх корней; контекстные
ошибки остаются в соответствующих каталогах. Каждый VO имеет собственный файл,
package __init__.py пустые. Агрегаты и Entity frozen в объектном срезе;
изменения состояния через replace/присваивание из Application не вводятся.

## **4. Декларативная схема, источники и валидация**

### **4.1. Пример определения**

Ниже только пример пользовательской схемы из двух полей, а не стартовый набор.
Feed также может не содержать ни одного текстового или денежного поля.
Default-выражение даёт +15% к regular; правило категории при наличии закупочной
цены — +25% к purchase. Сохранённое представление — AST, не исполняемая строка.
Тип поля и все его настройки вложены в type_definition; верхнего value_type нет.
Формат ещё не выпускался в persistence/API, поэтому целевой schema_format_version
остаётся 1. Совместимые aliases старой плоской формы и миграция не вводятся.

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
              },
              "purchase_source": {
                "provider": "supplier_sourcing",
                "path": "purchase_price",
                "selection": {
                  "mode": "SUPPLIER_SOURCE",
                  "supplier_source_id": "88888888-8888-4888-8888-888888888888"
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
дискриминатор string/text/money; будущий mapper выбирает класс VO и не передаёт
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
| type_definition.kind | string / text / money; определяет класс VO |
| type_definition.locale | Только STRING/TEXT, локаль либо null для языконезависимого текста |
| type_definition.currency | Только MONEY, необязательный код результата; null не наследует валюту источника |
| type_definition.value | Один типизированный способ получения значения |
| type_definition.fallback_policy | Только STRING/TEXT, явная политика отсутствующих переводов |
| type_definition.constraints | Текстовые ограничения длины либо денежные границы по типу |
| type_definition.transforms | Допустимые данному типу упорядоченные преобразования |
| export.enabled / name | Участие в выгрузке / имя колонки или тега |
| ai.instruction | Только метаданные будущего сценария |

Текстовые пути item.title/item.description не содержат языка; locale передаётся
в текстовом type_definition. NONE не подставляет другой перевод, LOCALE_CHAIN последовательно
проверяет заданные locales после целевой, MANUAL_REQUIRED требует ручного значения
при отсутствии целевого перевода. Фактическая локаль возвращается preview.
Цепочки конечны и не рекурсивны; языконезависимый текст не имеет fallback.

### **4.3. Структурная и семантическая проверка**

Первый Domain-срез проверяет собственные значения VO и согласованность
конструируемого Feed/Entity: типы, конечные числа, диапазоны, формы ID,
уникальность field_id/key/export.name и rule_id в пределах поля, порядок,
допустимые сочетания MONEY/text, структуру дерева/арность операций.
Прямые источники принимают только SourceProvider/CatalogSourcePath; неизвестный
или нетипизированный источник отклоняется уже при создании SourceReferenceVO.
Пустая схема допустима. Ошибка create/restore не создаёт частично валидный объект.

Draft сохраняет структурно корректное определение и может иметь семантические
issues, например известный Domain-источник с ещё не подключённым адаптером.
Неизвестный provider/path не сохраняется как семантический issue допустимого draft.
Частично введённая форма с
незавершённым деревом остаётся локальным UI draft и не подменяет Domain-объект.
При публикации полностью проверяются:

- Совместимость типов источников/параметров с полем, условиями и выражениями.
- Конечный числовой Decimal результата; валютная метка не участвует в арифметике.
- Известные операции, функции и точные схемы их параметров; обязательный ELSE.
- Допустимость операций для чисел, коллекций и UUID/строк/boolean.
- Поддержка локалей и прав на источник через справочники/Application Ports; форма необязательного кода валюты — через CurrencyVO.
- Валидность закупочной привязки для зависимости price.purchase.
- Совместимость ранее опубликованных field_id и override-контрактов.
- Хотя бы одно экспортируемое поле для Generic-профиля; безопасные XML-имена.
- Лимиты размера JSON, числа полей/правил/узлов, глубины AST, длины строк и
  числа операндов. Лимит байтов проверяется до декодирования на границе входа.

Чистые проверки находятся в Domain, получение внешних метаданных/прав — в
Application. Примеры title/price не создают скрытых проверок по ключу.

## **5. Infrastructure Layer — PostgreSQL**

### **5.1. Состав SQL-моделей**

Состав таблиц FeedBuilder для MVP:

| Таблица                      | Ответственность                    |
| ---------------------------- | ---------------------------------- |
| `fb_feeds`                   | Основные настройки Feed            |
| `fb_schema_drafts`           | Редактируемая схема                |
| `fb_schema_versions`         | Неизменяемые опубликованные версии |
| `fb_publications`            | Привязки товаров и overrides       |
| `fb_publication_projections` | Вычисленные значения и готовность  |
| `fb_generations`             | Запуски генераций                  |
| `fb_generation_issues`       | Ошибки и предупреждения            |
| `fb_artifacts`               | Метаданные CSV/XML                 |
| `fb_access_keys`             | Ключи доступа по URL               |

Дополнительно в `public` schema нужен реестр публичных идентификаторов Feed для маршрутизации в tenant.

Сейчас реализована только fb_feeds; остальные строки таблицы — будущие срезы.
Текущая схема хранится в fb_feeds.schema_definition. При будущем вводе ревизий
модель и перенос данных согласуются отдельно.

**Будущий draft хранится отдельно от опубликованных версий.** Это упрощает редактирование, блокировки и обеспечение неизменяемости опубликованной конфигурации. Все SQL-фрагменты ниже задают целевую структуру и реализуются tenant-миграциями Alembic с SQLAlchemy-моделями, mapper и репозиториями.

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

Для первого релиза `STRICT` — единственная политика: нельзя опубликовать новый файл с ошибочными товарами.
format_settings и product_mode хранятся в том же JSONB; отдельные колонки/таблицы
для настроек не нужны. При создании format_settings обязательно, defaults
применяются только к product_mode/validation_policy и параметрам выбранного VO.
Запись сохраняет полный снимок с явным format_settings.format и параметрами
одного формата; SQL-default для export_settings отсутствует.
Mapper преобразует product_mode в FeedProductMode, а format_settings.format выбирает
CsvExportSettingsVO/XmlExportSettingsVO; format не передаётся в конструктор VO.
При записи mapper явно берёт format.value из ClassVar: dataclass asdict сам по себе
ClassVar не добавляет. Готовые настройки передаются фабрике restore, собственные
инварианты проверяет Domain. Коллекция formats и отдельные csv/xml не поддерживаются;
persistence/API Feed CRUD реализованы без aliases старой формы.
Сейчас изменение формата/параметров увеличивает row_version. Отдельная
configuration_version и запуск сборки появятся с поведением генераций;
schema_format_version при изменении формата не меняется.

Текущая модель: infrastructure/persistence/models/feed.py.
Tenant-миграция 0020_feed_builder_crud следует за 0019_catalog_price_amounts,
проверена на новом tenant и при upgrade/downgrade существующего tenant.
Модель зарегистрирована в src/modules/tenant_persistence.py вместе с историческим
именем fb_feeds; autogenerate на head должен оставаться пустым.

schema_definition хранит канонический документ раздела 4 с полным порядком полей,
AI-метаданными, AST, закупочными bindings, constraints и transforms.
Application schema_document формирует документ результатов без I/O; Infrastructure
definition_mapper восстанавливает VO/Entity и контролирует входную форму/бюджеты.
FeedMapper.to_domain вызывает Feed.restore, который проверяет инварианты корня.
Строки Decimal не преобразуются в float; currency=None остаётся None.

Для текущего CRUD row_version соответствует Feed.version. UPDATE содержит ID
и ожидаемую версию в WHERE; ноль обновлённых строк означает конфликт.
get_for_update использует блокировку строки. Репозиторий не вызывает commit/rollback.
Именованное ограничение uq_fb_feeds_code переводится в FeedCodeConflictError;
остальные IntegrityError не маскируются. Архивный код остаётся занятым.

В будущем active_schema_version/active_generation_id/sequence/configuration_version
будут добавлены отдельными миграциями. Их нет в текущей таблице; SQL ниже описывает
будущие расширения и не выполняется миграцией 0020.

### **5.3. Будущие таблицы Schema**

В текущем срезе эти таблицы не создаются. Рабочее определение хранится в
fb_feeds.schema_definition, версия — fb_feeds.row_version. Следующий SQL и
описание публикации ниже относятся только к будущему согласованному срезу
ревизий. Ввод отдельных draft/version потребует самостоятельной миграции данных
и явного изменения контрактов; текущий PUT не использует nullable draft version.


```
CREATE TABLE fb_schema_drafts (
    feed_id UUID PRIMARY KEY
        REFERENCES fb_feeds(id),

    definition JSONB NOT NULL
        CHECK (jsonb_typeof(definition) = 'object'),

    row_version BIGINT NOT NULL DEFAULT 1,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE fb_schema_versions (
    feed_id UUID NOT NULL
        REFERENCES fb_feeds(id),

    version INTEGER NOT NULL CHECK (version > 0),

    definition JSONB NOT NULL
        CHECK (jsonb_typeof(definition) = 'object'),

    content_hash CHAR(64) NOT NULL,

    published_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (feed_id, version)
);

ALTER TABLE fb_feeds
ADD CONSTRAINT fk_fb_active_schema
FOREIGN KEY (id, active_schema_version)
REFERENCES fb_schema_versions(feed_id, version);

```

`fb_schema_drafts` содержит единственную рабочую версию для каждого Feed.

При публикации в одной транзакции:

1. Валидируем текущий draft.
2. Создаём новую строку `fb_schema_versions`.
3. Обновляем `active_schema_version`.
4. Удаляем draft.
5. Через domain-метод фиксируем FeedSchemaPublished; интеграционное сообщение записываем в Outbox той же транзакции до commit.

При повторном открытии редактора без сохранённого draft UI получает активную
схему и создаёт её локальную редактируемую копию. Query не изменяет БД.
SaveFeedSchemaDraft создаёт строку при первом сохранении с expected_version=null
и expected_schema_version; конкурентно созданный draft или смена активной схемы
возвращают 409. Следующие сохранения проверяют row_version существующего draft.

В дальнейшем можно реализовать несколько параллельных веток схем, но для MVP это не требуется.

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

    created_at TIMESTAMPTZ NOT NULL ,
    updated_at TIMESTAMPTZ NOT NULL ,

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

    schema_version INTEGER NOT NULL,
    publication_version BIGINT NOT NULL,

    catalog_revision TEXT NULL,
    configuration_version BIGINT NOT NULL,
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

Проекция устаревает при несовпадении schema_version, publication_version,
configuration_version, ревизий фактических источников
или при наступлении valid_until. Метаданные получаются через публичные порты,
без JOIN к таблицам чужих контекстов. События ускоряют инвалидацию, а проверка
ревизий/времени защищает от пропущенных событий. Для значений с override
ненужные автоматические зависимости не создаются.

Не требуется массово обновлять все 100 тысяч строк сразу после публикации новой схемы. Их устаревание можно выявлять по несовпадающим версиям.

### **5.6. Генерации, ошибки, артефакты**

```
CREATE TABLE fb_generations (
    id UUID PRIMARY KEY,

    feed_id UUID NOT NULL
        REFERENCES fb_feeds(id),

    definition_snapshot JSONB NOT NULL,
    as_of TIMESTAMPTZ NULL,
    request_sequence BIGINT NOT NULL,

    status TEXT NOT NULL
        CHECK (status IN (
            'PENDING', 'RUNNING',
            'SUCCEEDED', 'FAILED'
        )),

    attempt_count INTEGER NOT NULL DEFAULT 0,
    attempt_token UUID NULL,
    claimed_at TIMESTAMPTZ NULL,
    lease_until TIMESTAMPTZ NULL,
    failure JSONB NULL,

    total_items INTEGER NOT NULL DEFAULT 0,
    exported_items INTEGER NOT NULL DEFAULT 0,
    rejected_items INTEGER NOT NULL DEFAULT 0,

    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ NULL,
    finished_at TIMESTAMPTZ NULL,

    UNIQUE (feed_id, request_sequence),
    UNIQUE (feed_id, id)
);

CREATE TABLE fb_generation_issues (
    id UUID PRIMARY KEY,

    generation_id UUID NOT NULL
        REFERENCES fb_generations(id),

    publication_id UUID NULL,
    field_id UUID NULL,
    rule_id UUID NULL,
    expression_path TEXT NULL,

    severity TEXT NOT NULL,
    code TEXT NOT NULL,
    message TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX ix_fb_generation_issues_generation
ON fb_generation_issues(generation_id);

CREATE TABLE fb_artifacts (
    id UUID PRIMARY KEY,

    generation_id UUID NOT NULL
        REFERENCES fb_generations(id),

    format_code TEXT NOT NULL
        CHECK (format_code IN ('csv', 'xml')),

    storage_key TEXT NOT NULL UNIQUE,
    content_type TEXT NOT NULL,

    sha256 CHAR(64) NOT NULL,
    size_bytes BIGINT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (generation_id)
);

ALTER TABLE fb_feeds
ADD CONSTRAINT fk_fb_active_generation
FOREIGN KEY (id, active_generation_id)
REFERENCES fb_generations(feed_id, id);

```

Таким образом, Feed.active_generation_id указывает на конкретную успешную
генерацию с одним артефактом. UNIQUE(generation_id) ограничивает число артефактов
одним; format_code обязан соответствовать format_settings.format снимка генерации.
Переключение active_generation_id меняет единственный активный файл. История может
содержать генерации другого формата, но они не выдаются как параллельные активные файлы.
Метаданные итогового артефакта связываются с генерацией при complete в общей
транзакции с проверкой attempt_token; временные файлы попыток не создают второй
артефакт той же генерации.

Это целевое хранение следующего среза, не созданная миграция.
definition_snapshot сохраняет полную schema, export_settings и
calculation_engine_version из GenerationDefinitionSnapshotVO, без обязательного
FK к версии схемы. as_of восстанавливается в
GenerationCalculationContextVO; attempt_count/attempt_token/claimed_at/lease_until —
в число попыток и текущий GenerationAttemptVO. После завершения токен и lease
очищаются, число попыток сохраняется. failure восстанавливается в GenerationFailureVO.
Версии конкурентного сохранения и происхождение будущей опубликованной схемы
добавятся только вместе с соответствующим поведением.

При ошибке новой генерации указатель не изменяется.

### **5.7. Доступ по URL**

```
CREATE TABLE fb_access_keys (
    id UUID PRIMARY KEY,

    feed_id UUID NOT NULL
        REFERENCES fb_feeds(id),

    token_hash BYTEA NOT NULL CHECK (octet_length(token_hash) = 32),

    status TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'REVOKED')),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ NULL,
    CHECK (
        (status = 'ACTIVE' AND revoked_at IS NULL)
        OR (status = 'REVOKED' AND revoked_at >= created_at AND revoked_at IS NOT NULL)
    )
);

```

В `public` schema создаётся дополнительная таблица `feed_public_routes` с полями `public_id`, `tenant_id`, `feed_id`, `status`.

Она позволяет по публичному URL найти нужный tenant, не допуская прямого выбора SQL-схемы из пользовательского ввода.
fb_access_keys сохраняет отдельный агрегат FeedAccessKey. Выпуск секрета,
вычисление SHA-256 digest, однократная выдача и проверка доступа появятся
в Application/адаптерах. Сохранение ключа не требует загрузки всего Feed;
проверка существования фида и прав выполняется будущим сценарием.

### **5.8. Контекст расчёта и ревизии источников**

Правила и AST хранятся только в definition схемы. Их редактирование — обычный
SaveFeedSchemaDraft и PublishFeedSchema, без отдельных таблиц/назначений политик.
Поле schema_format_version определяет формат дерева, а calculation_engine_version
генерации — поддержанную семантику вычисления. Неподдерживаемая версия отклоняется.

В fb_publication_projections дополнительно сохраняются as_of, valid_until,
source_revisions: JSONB с ревизиями фактически использованных
Catalog/категорий/закупочных источников. valid_until — ближайшая известная граница
акции/временной зависимости, если она есть; computed_at не заменяет as_of.
На границе времени проекция STALE без ожидания события изменения товара.

В staging сохраняются фактические зависимости каждой записи: item/revisions,
идентификатор выбранного закупочного предложения, нужные временные границы,
применённый rule_id и числовые шаги формулы. Чувствительные суммы не копируются в общие логи.

FeedBuilder не имеет провайдера курсов, валюты вычислений или автоматической
конвертации. as_of фиксируется до первого расчёта и сохраняется для retry.
Пользовательский коэффициент хранится в AST: например, price.regular / 40 * 1.20.
Изменение коэффициента требует нового определения/задания; retry использует
прежний снимок формулы. Необязательная currency является только меткой поля.

configuration_version изменяется для влияющих на экспорт настроек Feed;
все определения полей/формул/порядка правил входят в schema_version. Row version
защищает конкурентное сохранение, не заменяет эти доменные версии.

## **6. Application: целевые порты, сценарии и транзакции**

Сценарии Feed CRUD уже реализованы. Остальные Application-контракты ниже
относятся к будущим срезам; их пустые заготовки не создаются.

### **6.1. Контракты хранения и внешних данных**

Write contracts FeedRepositoryProtocol, FeedPublicationRepositoryProtocol,
FeedGenerationRepositoryProtocol и FeedAccessKeyRepositoryProtocol принадлежат
Domain своих корней и работают с агрегатами. Draft/версии/правила сохраняются
через границу Feed; репозитории
для каждого VO, поля, правила или таблицы не создаются.

| Application Port / Service | Назначение |
| --- | --- |
| FeedQueryRepositoryProtocol | Списки/детали Feed и метаданные схем |
| FeedPublicationQueryRepositoryProtocol | Карточки, страницы, фильтры, статистика |
| FeedGenerationQueryRepositoryProtocol | История, issues и артефакты |
| FeedAccessKeyQueryRepositoryProtocol | Метаданные ключей без digest и секрета |
| SchemaVersionReaderProtocol | Immutable draft/опубликованные определения |
| PublicationProjectionPort | Условная запись и инвалидация проекций |
| CatalogProductReader | Batch простые позиции/выбранные варианты, принадлежность родителю, эффективный контент, regular/sale price, интервалы акций и ревизии |
| ProductParameterReaderPort | Batch зарегистрированные категории/SKU/другие параметры |
| PurchasePriceReaderPort | Batch закупочные цены по явной привязке источника |
| ReferenceDataReaderPort | Поддержка локалей; код валютной метки не требует курсового сервиса |
| ParameterRegistryPort | Типы, nullability, права, источники разрешённых параметров |
| SourcePathRegistry / FieldTypeRegistry / TransformRegistry | Метаданные допустимых источников/типов/преобразований и выбор handlers |
| PriceExpressionResolver | Application-координация входов, вызов чистого evaluator |
| FeedSerializerRegistry / FormatProfileRegistry | Сериализаторы и профили |
| ArtifactStorage / ExportStagingPort | Потоковые файлы и проверенные записи |
| GenerationJobPort / ProjectionJobPort | Транзакционная постановка/claim задач |
| OutboxRepositoryProtocol | Интеграционные сообщения в общей транзакции |
| PublicFeedRoutePort / FeedAccessPort | Доверенный public routing и ключи |
| Clock | Явное время preview/первого запуска и проверки актуальности |

Source adapter скрывает конкретный модуль и возвращает immutable snapshot,
не ORM/чужой агрегат. Метаданные вычислений не дают права читать закрытую цену.
Пакеты Catalog и Supplier Sourcing не импортируются во внутренний Domain Feed.
Если необходимого публичного чтения ещё нет, согласовать минимальный owner-контракт;
это не требует создания отдельного модуля прайс-листов.

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
| SaveFeedSchemaDraft — реализовано | feed_id, definition с полями/AST/bindings, expected_version = Feed.version | SaveFeedSchemaDraftResultDTO: feed_id, version, definition |
| PublishFeedSchema | feed_id, expected feed/draft versions | PublishFeedSchemaResultDTO: schema_version, content_hash |
| AddCatalogItemsToFeed | feed_id, item_references: пары catalog_item_id/catalog_variant_id | AddCatalogItemsToFeedResultDTO: mapping каждой пары → publication_id |
| RemoveFeedPublication | publication_id, expected_version | None |
| SetPublicationOverride | publication_id, field_id, value, expected_version | SetPublicationOverrideResultDTO: publication_version |
| ResetPublicationOverride | publication_id, field_id, expected_version | ResetPublicationOverrideResultDTO: publication_version |
| ChangePublicationStatus | publication_id, status, expected_version | ChangePublicationStatusResultDTO: status, version |
| RefreshPublicationProjection | publication_id | None |
| RequestFeedGeneration | feed_id, ожидаемая конфигурация | RequestFeedGenerationResultDTO: generation_id, PENDING |
| ExecuteFeedGeneration | generation_id, attempt_token | None, результат в агрегате |
| CreateFeedAccessKey | feed_id | CreateFeedAccessKeyResultDTO: ключ однократно |
| RotateFeedAccessKey | feed_id, key_id | RotateFeedAccessKeyResultDTO: новый ключ однократно |
| RevokeFeedAccessKey | feed_id, key_id | None |

Редактирование формулы/условий/порядка правил — сохранение draft FeedSchema,
не отдельный CRUD ценовых политик. При массовом обновлении поля/правила
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
| PreviewFeedPublication | publication_id, ACTIVE / DRAFT | PublicationPreviewDTO |
| PreviewFeed | feed_id, schema_mode, limit | FeedPreviewDTO |
| PreviewFieldCalculation | feed_id, catalog_item_id, catalog_variant_id или null, field_id, schema_mode, optional definition_override | FieldCalculationPreviewDTO |
| GetGeneration / ListGenerations | generation_id / feed_id и пагинация | GenerationDetailsDTO / Page[GenerationListItemDTO] |
| ListGenerationIssues | generation_id, фильтры/пагинация | Page[GenerationIssueDTO] |
| GetActiveFeedArtifact | feed_id | ActiveFeedArtifactDTO: формат, ссылка и метаданные единственного активного файла |
| DownloadPublicFeed | public_id, token, format | ArtifactDownloadDTO для streaming |

List/detail Queries читают проекции. Preview исполняет тот же Domain evaluator
на собранных snapshots без изменения бизнес-состояния. definition_override
позволяет проверить структурно корректное несохранённое определение поля,
проходит те же права/валидацию/лимиты и не публикует схему. As_of задаёт сервер.

### **6.4. UoW и события в следующих срезах**

Depends открывает UoW, собирает repositories/Outbox на одной сессии; обычный
handler получает порты, вызывает Domain и сохраняет результат. Commit выполняется
снаружи до HTTP-ответа, исключение откатывает процесс. Application не присваивает
поля агрегата, не открывает новый UoW и не получает AsyncSession.

Publish: проверить ожидаемые версии → получить метаданные/права → вызвать
чистую проверку структуры и эволюции → создать неизменяемую версию через Domain →
сохранить Feed/версию, удалить draft → Outbox до commit. События появляются только
в срезе поведения; создание/restore первого среза их не накапливает.

Сборка worker открывает собственные короткие UoW для claim, фиксации контекста,
heartbeat, complete и activation. Долгий resolve/storage не держит общую SQL-транзакцию.
Request-scoped session в worker не передаётся. При внешнем брокере используется
Outbox, а не неатомарная отправка после отдельного сохранения задания.

### **6.5. Версии и конкурентные изменения**

row_version: Feed, draft и публикация. Для ORM возможен version_id_col,
массовые UPDATE/DELETE явно проверяют expected version и число строк.
Конфликт — VERSION_CONFLICT / 409, не перезапись последним запросом.

schema_version включает условия, числовой AST и закупочные bindings; currency — метка определения поля.
configuration_version — настройки экспорта/выдачи, не дублирование версии формулы.
Повторная доставка задач идемпотентна, attempt_token защищает старый worker.
Ревизии источников и временная актуальность проверяются независимо от row_version.

## **7. Value Resolution Engine и параметры товара**

### **7.1. Источники и зарегистрированные параметры**

| Provider / path или parameter ID | Тип и смысл |
| --- | --- |
| catalog / item.title | Локализованный STRING |
| catalog / item.description | Локализованный TEXT |
| catalog / item.sku | Языконезависимый STRING |
| catalog / item.regular_price | Денежный источник без наценки |
| price.regular | Точная числовая сумма обычной продажной цены |
| price.sale | Действующая акционная цена на as_of, либо отсутствие |
| price.effective | Sale при действующей акции, иначе regular |
| price.purchase | Закупочная цена из явного purchase_source |
| product.category_ids | Набор явно назначенных UUID категорий |
| product.sku / product.id | SKU / идентификатор товара |

Все price.* передают числовые суммы как точные Decimal, без валютной размерности.
Код валюты Catalog/закупочного предложения не переносится в метку поля и не
вызывает автоматического пересчёта.

Это целевой потребительский контракт FeedBuilder, а не утверждение о готовом API.
Четыре прямых источника Catalog соответствуют SourceProvider.CATALOG и
CatalogSourcePath. Коды price.* и product.* в таблице — отдельные параметры AST,
а не дополнительные значения CatalogSourcePath. ParameterReferenceVO проверяет форму
ID; реализованная PriceCalculationSemanticPolicy проверяет закрытый реестр и типы
всех ветвей до чтения товаров. Сейчас реестр содержит только price.regular,
price.sale, price.effective, product.sku и product.id. price.purchase и
product.category_ids — будущие подключения, metadata/API их не предлагают;
новые/изменённые формулы с ними отклоняются.
Catalog уже хранит regular/sale и UTC-интервал действия акции. Supplier Sourcing
хранит purchase_price предложений. ProductParameterReader собирает категории
через публичную границу владельца, не через импорт ORM.

Каждый параметр имеет стабильный ID, тип, cardinality/nullability, разрешённые
операции и правила доступа. price.sale вне интервала акции отсутствует, хотя
в исходной спецификации может храниться запланированная sale price.
Если позднее понадобится необработанная плановая цена, вводится отдельный parameter ID.

Расширение реестра не требует нового поля SQL на каждую характеристику.
Параметры не обращаются к результатам других вычисляемых полей Feed в MVP.

### **7.2. Batch snapshots и закупочный источник**

CatalogProductReader получает пары catalog_item_id/catalog_variant_id и набор
целевых/fallback locales. Он возвращает immutable snapshots выбранных продаваемых
позиций, их роли/ID, принадлежности родителю, эффективного контента, спецификаций
цен и ревизий. Для SIMPLE субъект — сам товар; для VARIANT субъект — выбранный
вариант, catalog_item_id остаётся ссылкой на его родителя.

TITLE/DESCRIPTION разрешаются для выбранной позиции по правилам наследования
Catalog отдельно для каждой запрошенной locale; языковой fallback Feed применяется
по своей явной политике. SKU/regular/sale price принадлежат самой продаваемой
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

ProductParameterReader и PurchasePriceReader работают пакетно. PriceCalculationVO
при использовании price.purchase содержит purchase_source: PurchasePriceSourceVO
с supplier_source_id. Адаптер выбирает предложение этого источника для ID текущей
продаваемой позиции: SIMPLE либо выбранного VARIANT, а не автоматически для родителя.
Публичный owner-контракт закупки должен поддерживать такую привязку; предложения
родителя/других вариантов не подставляются вместо неё.
Ноль подходящих предложений — отсутствие значения, больше одного
без однозначного owner-контракта — PURCHASE_PRICE_AMBIGUOUS. Молчаливого выбора
минимальной/последней цены нет. Неактивное/недоступное предложение не подставляется.

Другие стратегии выбора закупки вводятся отдельными явными вариантами binding;
складская себестоимость не называется purchase_price без нового контракта.
Выбранный offer_id и revision возвращаются snapshot/trace. Binding хранится
в схеме и наследует её версионирование, исходные предложения не копируются.

Потребности собираются из definition до чтения, без N+1 на каждый узел AST.
Для conditional price.purchase сначала проверяются требуемые ветви/параметры;
адаптер может batch-предзагрузить кандидатов, но отсутствие значения в
неиспользованной ветви не становится блокирующим issue.

### **7.3. Контекст разрешения**

ResolutionContext содержит tenant/feed/publication IDs, catalog_item_id,
catalog_variant_id или null и ID выбранной продаваемой позиции, schema_version,
configuration_version, as_of, calculation_engine_version и generation_id
при экспорте. Локаль берётся из StringFieldTypeVO/TextFieldTypeVO, необязательная
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
готовности. Неподдерживаемое определение выявляется при publish независимо от ветви.

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

Проекция хранит версии схемы/публикации/конфигурации, source revisions, as_of,
valid_until. При условном upsert старый worker не перезаписывает новый.
Текущий список читает проекции, preview и экспорт вычисляют результат заново.
Зависимости override и неприменённых ветвей не включаются как нужные для результата.
Сведения для EXISTS/IS_MISSING и проверенных условий также являются зависимостями:
появление ранее отсутствовавшего значения должно инвалидировать проекцию.

## **8. Условия и формулы денежного поля**

### **8.1. Область действия и способы получения значения**

Правила принадлежат конкретному MONEY-полю конкретной версии FeedSchema.
Они не записываются в Catalog и не назначаются другим Feed автоматически.
Несколько денежных полей могут независимо рассчитывать розничную/партнёрскую/
акционную цену и цену в другой валюте. Ключ поля не влияет на семантику.

MoneyValueDefinitionVO имеет режим SOURCE, MANUAL или CALCULATED. Последний
содержит PriceCalculationVO: rules, default_expression
и optional purchase_source при зависимости price.purchase. Процент/фиксированная
надбавка в UI — удобный способ построить выражение конечной цены.
PriceAmountVO содержит только сумму. Необязательная currency принадлежит полю;
PriceValueVO объединяет сумму и выбранную метку при разрешении значения.

### **8.2. Выбор IF / ELSE IF / ELSE**

```text
IF категория содержит выбранный UUID AND purchase_price EXISTS
    THEN purchase_price × 1.25
ELSE IF sale_price EXISTS
    THEN sale_price × 1.10
ELSE
    regular_price × 1.15
```

Правила проверяются последовательно. Первое истинное условие выбирает единственное
выражение; остальные правила не исполняются. Если совпадений нет — обязательный
ELSE/default_expression. Пустой список rules допустим. Эффекты/наценки правил
не суммируются и не применяются каскадом. Порядок — часть версии схемы.

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
Дополнительные бренд/поставщик/характеристики подключаются через ParameterRegistry
с явным типом и источником, не произвольным getattr/SQL/URL.

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
IF purchase EXISTS → purchase*1.25, ELSE regular*1.10.

| Код | Причина |
| --- | --- |
| CALCULATION_PARAMETER_MISSING | Нужный выбранной ветви/условию параметр отсутствует |
| PURCHASE_PRICE_AMBIGUOUS | Закупочный источник не дал единственного предложения |
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

Изменение правила сохраняется в draft через корень Feed. При publish меняется
schema_version; активная выгрузка остаётся прежней до успешной новой генерации.
Копирование поля/правила создаёт новые ID. Редактирование внутри того же поля
сохраняет field_id/rule_id; порядок правил и формулы входят в опубликованный снимок.

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

Текущий AddCatalogItems использует сохранённый Feed без требования опубликованной
схемы. Application проверяет права, получает Feed и внешние факты
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

SetPublicationOverride проверяет expected_version, field_id активной схемы и
базовый входной тип, вызывает Domain публикации и сохраняет её/инвалидацию
в одной транзакции. Сумма передаётся Decimal-строкой и создаёт PriceAmountVO;
валюту override не принимает. Пустое/некорректное представление числа отклоняется.
Нарушение max_length/min_amount может сохраняться как ввод с INVALID.
Ручная цена не проходит формулу/наценку источника, но transforms и constraints
проверяются. Currency результата берётся только из определения поля.

Reset удаляет запись override отдельным действием с версией публикации.
После сброса снова применяется type_definition.value_definition поля.
Ручной null — не reset.
Удалённое дополнительное поле не уничтожает автоматически его старые overrides:
они не исполняются/не экспортируются, а повторное использование ID с иным смыслом
запрещает проверка опубликованных контрактов.

### **9.3. Preview**

PreviewFeedPublication использует ACTIVE или сохранённый DRAFT и возвращает
полностью вычисленные поля. Отсутствие draft показывается явно. PreviewFeed
ограничивает первые N публикаций и использует тот же resolver/profile/serializer.
PreviewFieldCalculation проверяет выбранную пару catalog_item_id/catalog_variant_id
и конкретное денежное поле, включая optional несохранённое определение после
структурной проверки. Для варианта preview использует тот же эффективный контекст,
что публикация и экспорт; ID родителя не подменяет выбранную позицию.

Preview ничего не публикует и не создаёт бизнес-draft. Общие as_of и снимки определений обеспечивают
согласованное сравнение результатов одного запроса; повторный preview может взять
новое время/исходные ревизии. Trace фильтруется правами; режим тестирования не
позволяет обойти закрытые закупочные данные или проверить произвольный код.

### **9.4. Проекции и участие**

Refresh получает snapshots, выполняет resolve и условно записывает проекцию при
актуальных schema/publication/configuration revisions и ревизии задачи расчёта.
Результат старого worker отбрасывается. Массовое мгновенное обновление после
publish не требуется — несовпадение версий определяет STALE лениво.

valid_until проверяется при чтении/следующем resolve; граница акции делает кеш
устаревшим без события изменения. Это не равно автоматической генерации по расписанию:
активный файл меняется только новым Generation Request. Списки показывают дату
расчёта/устаревание и не обещают цену реального времени в уже выпущенном артефакте.

В экспорт входят только ENABLED. Изменение участия/удаление привязки проходит
через Domain публикации и не меняет Catalog. Исторические issues сохраняют
безопасные сведения даже после удаления текущей публикации.

## **10. Генерация CSV/XML**

### **10.1. Внутренняя экспортная модель**

Сериализатор получает динамический список типизированных значений. Он не знает специальных ключей title/price, структуры AST или закупочных источников.

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
MONEY записывается десятичной суммой; заданная метка становится атрибутом
currency: <price currency="USD">25.00</price>. При currency=None атрибут отсутствует:
<price>25.00</price>. Это представление значения, не дополнительное поле схемы.
Для отсутствующего необязательного значения
Generic CSV записывает пустую ячейку, Generic XML опускает элемент; профиль
может явно задать другое представление, не меняя FieldValueResolver.

`write_element()` должен экранировать спецсимволы XML и отклонять недопустимые символы XML 1.0. Имена тегов валидируются при публикации схемы.

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

### **10.6. Точность и профиль формата**

Serializer не выполняет арифметику, дополнительную наценку и скрытое округление.
Количество знаков следует явным настройкам/разрешённой точности. Формат с двумя
знаками применяется только после соответствующего полевого округления либо
если значащие разряды не теряются. Все вычисленные числа сериализуются десятично.
Поле constraints.required — пользовательское, требования площадки — профильные.
Пресет только заполняет исходную схему, не заменяет FormatProfile-валидацию.

## **11. Асинхронная генерация и атомарная выдача**

### **11.1. Полный процесс**

```text
RequestFeedGeneration: PENDING + полный снимок schema/export settings/engine version
  → claim: RUNNING, attempt_token, lease
  → однократная фиксация as_of; пользовательский курс уже записан в AST
  → выбранные ENABLED-публикации SIMPLE/VARIANT по снимку Product Mode
  → batch выбранных позиций, нужного контекста родителей и разрешённых параметров
  → override либо выбор IF/ELSE и выражение → transforms → constraints
  → staging ExportRecord + фактические source revisions/trace metadata
  → один CSV либо XML согласно снимку format_settings
  → один неизменяемый артефакт
  → SUCCEEDED
  → условная атомарная активация единственного артефакта
```

### **11.2. Запрос и фиксированный контекст**

В короткой общей транзакции Request проверяет Feed/опубликованную схему,
выделяет sequence через Domain и сохраняет FeedGeneration PENDING с полным
GenerationDefinitionSnapshotVO схемы, настроек и calculation_engine_version.
definition_snapshot.export_settings содержит явный product_mode=VARIABLE_TO_SINGLE и один
format_settings с фиксированным format и всеми параметрами выбранного VO.
Worker использует снимок задания, preview — выбранные настройки Feed;
оба вызывают общую стратегию. Retry использует сохранённый код, а не текущий
default. Изменение CSV/XML или delimiter/имён XML требует новой конфигурации
и задания; retry не подмешивает текущие параметры. Экспорт не раскрывает заново
список вариантов Catalog.
Будущий Domain не позволяет запрашивать генерацию DRAFT/PAUSED/ARCHIVED Feed;
активируется Feed с опубликованной непустой экспортной схемой. Правка draft
не влияет на текущую опубликованную версию и активную выдачу.

PostgreSQL может быть очередью: PENDING захватывается FOR UPDATE SKIP LOCKED,
RUNNING получает уникальный attempt_token/lease. При внешнем брокере постановка
идёт через Outbox в общей транзакции. Repo не выполняет commit.

До первого resolve атомарно фиксируется as_of. Retry использует то же время,
снимок схемы/AST и числовые константы, включая пользовательский курс.
Валютных провайдеров, FX-снимков и валюты расчёта нет. Необходимые исходные
цены/параметры получаются через Application по ленивой семантике выражений.

### **11.3. Выполнение и транзакционные границы**

Worker читает точный снимок схемы/AST/закупочных bindings из задания, не текущий draft.
Пакеты ENABLED идут в стабильном keyset-порядке, начальный размер 500.
Потребности контента/цен/категорий/закупки собираются пакетно, без N+1 по полям
и узлам. Внутри одного вычисления наценка не применяется повторно; разные поля
имеют независимые определения. Override исключает ненужные входы своего поля.

Чистый evaluator получает as_of и доступные snapshots, не выполняет I/O.
Если нужен дополнительный вход, Application получает его в рамках
зафиксированного контекста до чистого шага. Новая формула или изменение
коэффициента курса требует нового задания; текущая попытка использует
прежний снимок определения.

При STRICT и issue у ENABLED-публикации — FAILED с issues/counts, без переключения
выдачи. Иначе ExportRecord сохраняются в staging, затем единственный сериализатор
создаёт файл с параметрами из снимка format_settings. Storage key уникален для
попытки/артефакта, сохраняются sha256, size и content-type. Временный файл не
активируется до успешного завершения генерации.

Claim, heartbeat, capture context, complete и activation — короткие отдельные
UoW во внешнем worker bootstrap. Долгое чтение/расчёт/storage не держит SQL-транзакцию.
Каждая запись результата проверяет attempt_token: потерявший lease worker
не может завершить или активировать результат. Async cancellation не подавляется.

### **11.4. Активация, retry и согласованность**

Успешная генерация активируется, только если:

- она принадлежит Feed и имеет SUCCEEDED;
- единственный требуемый артефакт сохранён, проверен и соответствует формату снимка;
- схема и настройки definition_snapshot соответствуют текущему определению
  для выдачи; дополнительные версии конкурентной конфигурации будут введены
  вместе с поведением Feed, а не с текущими фабриками объектов;
- Feed допускает активацию, sequence не старее уже активной;
- попытка не потеряла право завершения, публикация результата идемпотентна.

Под блокировкой Feed условно меняется один active_generation_id и его sequence.
Активируется один файл. При смене CSV на XML или наоборот предыдущий файл остаётся
активным до успешной активации новой генерации; после неё старый исторический
артефакт не выдаётся как второй активный файл.
Повтор активации того же результата — no-op.
Изменившаяся схема/настройки дают SUCCEEDED без активации с понятной причиной.
Attempt token проверяется при complete в RUNNING. Для уже сохранённого SUCCEEDED
повторную активацию может выполнить отдельный идемпотентный процесс без продления
lease завершённой попытки. После сбоя между complete/activation активацию можно повторить. Более старый
запрос не заменяет уже активный более новый; ещё не завершившийся новый запрос
сам по себе не запрещает активировать более ранний успешный результат.

Завершение акции после capture не отменяет результат с зафиксированным as_of.
Новая формула или пользовательский коэффициент не подменяют снимок запущенного
задания. Следующая генерация получит новую конфигурацию/время.
UI показывает as_of и время создания. Автоматическая перегенерация — будущее расписание.

MVP не имеет единого transaction snapshot всех независимых источников и набора
публикаций на начало прохода. Используются данные фактически прочитанных ревизий;
они сохраняются по записи. Retry сохраняет конфигурацию/as_of и константы формулы, но может прочитать
более новые ревизии Catalog/закупки. Полное побитовое воспроизведение из внешних
источников не обещается; CSV/XML одной попытки одинаково опираются на staging.

Временные технические сбои повторяются с лимитом/backoff, ошибки бизнес-валидации
не ретраятся автоматически. Cleanup удаляет незавершённый staging/осиротевшие файлы
по retention с проверкой активных попыток/ссылок. Counts: total_items — выбранное
количество позиций прохода, rejected_items — позиции с blocking issues,
exported_items — подготовленные корректные записи, включая staging.
При FAILED частичные счётчики сохраняются для диагностики, но итоговый артефакт
отсутствует. Счётчик не означает публичную выдачу. В SUCCEEDED учтены все
выбранные позиции, а STRICT требует rejected_items=0. Объектный срез проверяет
согласованность этих значений, но не исполняет перечисленные процессы.

### **11.5. Публичная раздача**

```text
https://feeds.example.com/f/{public_id}/{token}/catalog.csv
https://feeds.example.com/f/{public_id}/{token}/catalog.xml
```

Public registry разрешает public_id в доверенный tenant, Tenancy/admission
подключают tenant, FeedAccess проверяет хеш токена/отзыв, read-side находит
единственный активный артефакт. Расширение URL проверяется по формату именно
активной генерации: XML не отдаётся по .csv и наоборот, несовпадение — 404.
До успешной активации нового формата прежний URL/Content-Type сохраняются;
после активации доступен только URL нового активного формата. Нет активной выдачи —
404. UoW и DB-проверки завершаются
до streaming; сессия/ORM не живут вместе с долгой HTTP-передачей файла.

Поддержать ETag, Last-Modified, Content-Type и HTTPS. Токен показывается однократно,
в SQL хранится криптографический хеш. Отзыв/ротация прекращают старый доступ;
кеш не обходит авторизацию. По умолчанию замена отзывает заменяемый ключ атомарно,
дополнительные ключи имеют независимый lifecycle. Application/access logs исключают
токен из URL. При FAILED новый файл не публикуется, старая ссылка работает.

## **12. Presentation: целевой REST API**

Feed CRUD, GET схемы, PUT рабочего определения и три реестра метаданных
реализованы; остальные маршруты — будущие срезы.
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
| GET | /feeds/{id}/schema | GetFeedSchema: текущая рабочая схема, без ACTIVE/history |
| PUT | /feeds/{id}/schema/draft | SaveFeedSchemaDraft, включая AST/правила/bindings |
| POST | /feeds/{id}/schema/publish | PublishFeedSchema |
| POST | /feeds/{id}/preview | PreviewFeed |
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
конфигурацию; метаданные активного файла появятся вместе с генерациями.
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
BIGINT) и полный definition. Отдельной версии draft нет, null запрещён.
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
resolved_value содержит только amount. Фиктивных schema/config/publication versions нет.

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

Для цены из карточки используется существующий POST /feeds/{id}/calculation-preview:
пара IDs берётся из публикации, поле — из сохранённой схемы. MANUAL требует будущего
редактора значений. Preview сохраняет существующие права, Decimal и отсутствие FX.

Следующая часть добавит Set/ResetPublicationOverride и PreviewFeedPublication
всех полей с readiness, а затем постоянные проекции; эти методы пока не реализованы.

### **12.3. Генерации и ключи**

| Метод | Путь | Назначение |
| --- | --- | --- |
| POST | /feeds/{id}/generations | RequestFeedGeneration |
| GET | /feeds/{id}/generations | ListGenerations |
| GET | /generations/{id} | GetGeneration |
| GET | /generations/{id}/issues | ListGenerationIssues |
| GET | /feeds/{id}/artifact | Единственный активный файл и его фактический формат |
| POST | /feeds/{id}/access-keys | Создать ключ |
| POST | /feeds/{id}/access-keys/{key_id}/rotate | Ротация |
| DELETE | /feeds/{id}/access-keys/{key_id} | Отзыв |

### **12.4. Preview DTO и объяснение цены**

Backend возвращает publication_id, catalog_item_id/catalog_variant_id,
status/readiness, schema/config versions,
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
Коды включают FEED_NOT_FOUND, SCHEMA_NOT_PUBLISHED, INVALID_SCHEMA,
UNKNOWN_FIELD, UNKNOWN_SOURCE_PATH, SOURCE_TYPE_MISMATCH,
REQUIRED_VALUE_MISSING, MAX_LENGTH_EXCEEDED,
TRANSLATION_MANUAL_REQUIRED, VERSION_CONFLICT, SOURCE_UNAVAILABLE,
UNKNOWN_CALCULATION_PARAMETER и вычислительные коды раздела 8.6.

Запись передаёт expected_version агрегата/draft и получает новую версию;
В текущих save draft/preview expected_version — обязательная положительная
Feed.version. Отдельные версии/expected_schema_version появятся вместе с будущим
жизненным циклом публикации схемы.
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
Выбор товаров, публикация, сборка файлов и ключи остаются отдельными срезами.

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
Поля с неподключёнными закупкой/категориями остаются read-only; их AST/AI/bindings
передаются без потерь при редактировании остальных полей.

«Сохранить схему» проверяет весь локальный draft и отправляет полный снимок.
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
настройка значения публикации, не защита поля. Publish проверяется backend.

Inspector: key/label/type, язык либо валюта результата, способ получения значения,
fallback, constraints, transforms и export. Смена смысла опубликованного ID
показывает необходимость нового поля, но пользователь не обязан создавать новый Feed.
Дерево будущих групп/массивов не имитируется неработающими элементами MVP.

Page оркестрирует toolbar/save/preview/publish, palette/canvas/inspector — UI
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
  │    ├── PurchaseSourceBinding
  │    ├── DefaultExpressionEditor (ELSE)
  │    └── OrderedRuleList
  │         └── Rule: ConditionBuilder (IF) + ExpressionEditor (THEN)
  ├── Transforms / Rounding
  ├── Constraints / Export
  └── TestOnProduct → серверный preview/trace
```

Правило можно добавить/отредактировать/удалить/переместить с сохранением rule_id;
копия получает новый ID. Видно «первое совпадение», обязательный ELSE и отсутствие
автоматического суммирования правил. Category selector работает с UUID и labels,
не сохраняет label как условие. Исходная закупка выбирается явно; неоднозначность
показывается, не решается случайным первым предложением.

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
override без изменения опубликованной схемы.

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
одного денежного поля. Новые формулы или значения здесь не сохраняются.

Следующая часть: редактор динамических полей, manual overrides/reset и полный
PublicationPreviewDTO/readiness. Пользовательские колонки и серверная фильтрация
по готовности появятся вместе с полноценным resolver/проекциями.

### **13.5. Экспорт и история**

Экран показывает активную генерацию, as_of, время создания, товары/размеры,
одну ссылку на активный файл с его форматом, Generate, progress, history, issues
и управление ключами. Текущая конфигурация и формат активного файла показываются
отдельно, если новая генерация ещё не активирована.
При FAILED последнего запуска явно указано, что публичная ссылка выдаёт предыдущий
успешный файл. Изменение draft не обещает немедленную смену выгрузки.

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
frontend-модели, передают AbortSignal, keys включают tenant/ID/schema-mode,
фильтры/пагинацию и входы preview. Any не заменяет типизированное дерево.

Server state — TanStack Vue Query, session — существующие stores. URL/page state
владеет поиском/пагинацией/вкладками; форма — несохранённым draft и полями.
Refetch не стирает ввод. Save очищает только отправленный snapshot, сохраняя
изменения во время запроса. 409 показывает конфликт и позволяет сохранить свой ввод.

Mutation инвалидирует соответствующие detail/list/schema/preview keys:
publish — активную схему и проекции, override — карточку/статистику, настройки —
Feed/preview. Тестовый preview ничего не инвалидирует как запись. Повторный submit
заблокирован pending; неоднозначное создание не повторяется с риском дубля.
Смена tenant отменяет запросы, очищает старый draft/cache, игнорирует поздние ответы.
Polling generation останавливается на результате и при уничтожении владельца.

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
Public route разрешается только через доверенный registry/Tenancy admission.
Нельзя выбрать чужой tenant, SQL-схему, offer/source или Catalog item по произвольному
UUID без проверки доступа. Никаких ORM imports/SQL JOIN чужих контекстов.

Права разделяют просмотр/редактирование Feed, схемы/формул, overrides, запуск,
ключи и доступ к защищённым параметрам. Разрешение использовать закупочную цену
в расчёте/публичном результате должно быть явным: производная цена может раскрывать
исходную стоимость. Отдельно разрешается детальный trace с защищёнными входами.
Скрытие столбца в UI не заменяет backend-проверку; произвольная формула, condition
и definition_override не обходят запрет доступа. Пресеты будущего не повышают права.

Источники/параметры/операции зарегистрированы. JSON/AST не содержит исполняемых
Python/JS/SQL, произвольного URL, доступа к файлам или окружению. Лимиты:
байты definition до декодирования, поля/правила/узлы/глубина, длины literals,
коллекции условий, preview, batch, число генераций и время/бюджет evaluator.
Все ветви проверяются структурно/по типам при publish, даже если не исполняются.

CSV имеет явную политику значений, похожих на формулы таблиц, без молчаливого
искажения машинного импорта. XML экранируется, имена/символы валидируются.
Доступ к артефакту проверяется до streaming и не обходится кешем после отзыва.
Ключи хешируются, выдаются однократно, отсутствуют в access/application logs.

Domain не логирует. Application/worker логируют безопасные tenant/feed/generation
IDs, попытку, длительность и reason_code. Committed — после успешного commit;
один технический сбой со stack trace записывается на одной границе. В логи не
передаются целиком DTO/AST/trace, закупочные суммы, токены и персональные данные.

Метрики: размер/длительность генерации, queue/lease/retry/fencing, FAILED,
число issues/экспортированных товаров, возраст активного артефакта, STALE,
время evaluator, batch/query count. Ожидаемая ошибка значения не становится
технической ERROR автоматически. Retention учитывает активные файлы, snapshots
и историю; незавершённые staging очищаются без удаления живой попытки.

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
- Собственные настройки проверяют VO типов; PriceCalculationStructurePolicy
  проверяет ID/бюджет/закупочную зависимость при create/restore поля и восстановлении
  Feed без выбора ветви, вычислений и обращения к внешнему реестру параметров.
- Нет evaluator, редактора полей/публикации схемы/генерации, событий и запросов
  к справочникам. Репозиторий и внешние слои есть только у Feed CRUD.

Это критерии именно первого среза. Исполнение if/арифметики и full publish-проверка
не требуются до реализации соответствующих следующих срезов.

#### **15.1.1. Объекты Publication, Generation и AccessKey**

Тесты test_feed_builder_execution_domain.py дополняют проверки Feed:

- FeedPublication.create создаёт ENABLED без overrides для SIMPLE и конкретного
  VARIANT; restore сохраняет все поля для каждого статуса.
- Ссылка требует типизированные различные ID; Domain не импортирует Catalog.
- Строка, PriceAmountVO и явный None сохраняются; отсутствующий override не равен None.
  Неподдержанные значения/повтор field_id/неверные даты отклоняются.
- Входные списки overrides копируются; изменение списка не меняет объект.
- FeedGeneration.create формирует PENDING для CSV и XML с полным снимком
  и режимом VARIABLE_TO_SINGLE. Restore сохраняет каждое поле всех четырёх статусов.
- Несогласованные попытка/даты/контекст/счётчики/ошибка/файл отклоняются.
  RUNNING допускает отсутствие ещё не зафиксированного контекста только до
  обработки позиций. Истёкший lease восстанавливается без чтения часов.
- Повторная попытка сохраняет прежнее as_of и снимок числовой формулы.
- PriceAmountVO сохраняет точность без валюты/округления; NaN/Infinity/float/bool
  и превышение структурного бюджета отклоняются. Ноль/отрицательное число допустимы.
- Валюта MONEY необязательна: отсутствие/None/код проходят create/restore,
  не меняют формулу и не наследуют код источника. Ручной Shared MoneyVO отклоняется.
- Calculation currency, MoneyLiteralVO и FX-объекты удалены; старые kwargs
  отклоняются без compatibility aliases.
- SUCCEEDED требует полный STRICT-результат и один файл нужного формата.
  FAILED сохраняет причину и может сохранять частичный прогресс без итогового файла.
- Снимок не обходит уникальность полей и проверку Entity FieldDefinition:
  обе фабрики генерации вызывают FeedSchemaStructurePolicy.
- FeedArtifact.create/restore сохраняют все метаданные; размер/MIME/checksum/даты
  и соответствие формата проверяются, файл не читается.
- FeedAccessKey.create создаёт ACTIVE без revoked_at; restore сохраняет ACTIVE
  и REVOKED, отвергает несогласованные статусы/даты и невалидный digest.
  Только immutable bytes длиной 32; digest исключён из repr.
- Строки/чужие enum вместо enum, сырые структуры вместо VO, bool вместо счётчиков
  не принимаются. Все ID/время передаются явно.
- Архитектурные проверки обходят все четыре корня и их зависимые Entity/VO:
  create/restore плюс change_settings/archive только у Feed, __post_init__ только
  у VO; пустые __init__.py, прямые импорты, аннотации/docstrings и чистый Domain.
  Остальные слои есть только у Feed; связи агрегатов по ID, ревизий нет.

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

Архитектурные тесты разрешают только текущее поведение Feed и его внешние слои.
Publication/Generation/AccessKey по-прежнему имеют только объекты Domain.
Существующие metadata/registration/tenant-migration проверки остаются обязательными.

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
ввод, точность Decimal-строк за диапазоном Number, AST/AI/bindings round-trip,
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
| Изменение draft после publish | Опубликованный снимок не меняется |
| Формула/условие/порядок изменены | Новая schema_version после publish |
| Два истинных правила | Выполняется только первое |
| Ни одно правило не подошло | Выполняется default_expression |
| ALL/ANY/NOT | Типы/арность и короткое замыкание соблюдены |
| Ошибка выбранного условия/формулы | Не считается False и не переходит скрыто к ELSE |
| Отсутствие в неприменённой ветви | Не блокирует результат |
| EXISTS/IS_MISSING, 0, False, пустой набор | Отсутствие не смешивается со значением |
| Нет закупки, есть ELSE regular | Явная ветвь корректно возвращает цену |
| Источник закупки неоднозначен | PURCHASE_PRICE_AMBIGUOUS |
| Категория UUID | Точное членство, не имя/не неявные предки |
| Regular=1000 UAH, множитель 1.20 | 1200 UAH до иных transforms |
| Purchase=800 UAH, множитель 1.25 | 1000 UAH, Catalog не изменён |
| Sale вне/на границах [from,to) | Корректное отсутствие/выбор effective по as_of |
| Типы денег/чисел, деление на ноль | Предсказуемые результаты/ошибки, без float |
| Разные исходные валюты | В арифметику входят только суммы; пересчёт задан пользователем в формуле |
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
round-trip product_mode в настройках/снимке генерации, optimistic versions Feed/draft/
publication, общий UoW и атомарный Outbox. Restore не подменяется mapper-инвариантами.
Проверить schema_translate_map, public routing и два tenant, включая закупочные
source IDs/offer IDs/артефакты. Прямого чтения чужих таблиц нет.

Проверить условную запись проекций по ревизиям/времени, valid_until на границе
акции без update-события, появление ранее отсутствующей зависимости, invalidation
по изменению AST/категории/закупочной цены/коэффициента формулы. EXPLAIN/query count и batch
исключают N+1 на каждый товар/поле/AST-узел.

### **15.4. Генерация и сериализация**

- Кириллица, кавычки/запятые/переносы CSV, безопасные XML-имена/escaping/символы.
- Произвольные колонки, отсутствующее необязательное значение и явная точность.
- Единственный выбранный сериализатор читает staging, не меняет цену/правила.
- CSV Feed создаёт один CSV, XML Feed — один XML; второй формат не исполняется.
  Снимок/retry сохраняет format_settings и его параметры; UNIQUE(generation_id)
  не допускает второй артефакт той же генерации.
- VARIABLE_TO_SINGLE даёт одну запись на публикацию без родителя и группировки;
  снимок задания содержит режим, retry не подменяет настройки текущими/defaults.
- Один as_of и снимок формулы; изменение пользовательского курса в новом
  определении не меняет retry уже запрошенной генерации.
- Изменён draft — активная схема прежняя; publish другой версии запрещает
  активацию старого результата, прежняя активная выдача сохраняется.
- Старый запрос завершился позднее нового — sequence не откатывает выдачу.
- Повтор/истёкший lease/старый attempt_token — без двойной активации.
- Смена CSV на XML/обратно увеличивает configuration_version, не версию схемы.
  Ошибка нового запуска сохраняет старый активный файл; успешная активация заменяет
  его одним новым. URL-расширение и Content-Type соответствуют активной генерации,
  исторический файл не становится вторым активным артефактом.
- Источники недоступны технически — ограниченный retry; ошибка формулы — FAILED без retry.
- Полностью ручные поля не требуют ненужных исходных цен.
- Отзыв/ротация ключа работают с HTTP cache; streaming не держит DB-транзакцию.
- Большой Catalog: ограниченные память/staging, keyset, heartbeat и cleanup.

### **15.5. API, UI и E2E**

```text
CreateFeed (пустая схема, явно выбранный CSV либо XML)
  → SaveFeedSchemaDraft (пользовательские поля, IF/ELSE/AST)
  → PreviewFieldCalculation
  → PublishFeedSchema
  → AddCatalogItemsToFeed
  → PreviewFeedPublication
  → SetPublicationOverride / ResetPublicationOverride
  → RequestFeedGeneration / ExecuteFeedGeneration
  → Download выбранного CSV либо XML
```

Повторить с двумя Feed с разными формулами, несколькими языками/валютами,
категорией, выбранной закупкой, активной/закончившейся акцией, ручной ценой,
ошибочным новым выражением и сохранением старой выдачи. Tenant isolation и
права защищённых входов проверяются через реальные API/БД.

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

#### **16.1.1. Domain Publication, Generation и AccessKey: объектный срез**

FeedPublication с выбранной позицией/overrides; FeedGeneration с полным снимком,
попыткой, расчётным контекстом и зависимым FeedArtifact; самостоятельный
FeedAccessKey с digest и датой отзыва. Только create/restore и проверки.
Общие ошибки/валидация находятся на уровне Domain; правила структуры схемы
повторно используются фабриками Feed и FeedGeneration через чистую Policy.

Готовность: все тесты 15.1.1 и существующие тесты Feed проходят.
У Publication/Generation/AccessKey нет бизнес-методов, контрактов хранения или
внешних слоёв. Ревизий, событий и evaluator нет.
Наличие объектов не означает возможность реально привязать Catalog, собрать
файл, выпустить секрет, отозвать доступ или переключить публичную выдачу.

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

### **16.2. Поведение Domain и жизненный цикл схемы**

Редактирование полей/правил через корень, сохранение идентичности/порядка,
draft/publish/immutable snapshots, проверка эволюции field_id, статусы Feed,
версии конфигурации, события и Domain repository contract. Здесь же вводятся
объекты результатов/ошибок поведения без HTTP/ORM. Нет конкретных ключей,
обязательных для каждой схемы; пустой draft допускается.

Готовность: операции атомарны в памяти, не оставляют частичных мутаций/событий,
публикация валидирует состав и сохраняет неизменяемую версию. Внешние метаданные
передаются snapshots; обращения к справочникам не попадают в Domain.

### **16.3. Persistence Foundation**

Tenant Alembic-миграции, SQLAlchemy models, mappers create/restore, write/query
repositories, UoW, версии и Outbox, public route registry. Сохраняются AST/bindings
и Decimal; нет таблиц отдельных ценовых политик. Код группируется по корням.

Готовность: round-trip и конкурентные/tenant tests; invariant не перенесён в mapper.

### **16.4. Feed CRUD и конструктор схемы**

Application Command/Query/DTO, Depends, HTTP методы, метаданные типов/источников/
параметров/операций, создание пустого Feed, save/publish. Vue Page/model/UI,
свободные поля, AST редактор IF/ELSE и источника закупки, сохранность draft.
Export Settings/API/DTO явно сохраняют единственный product_mode=VARIABLE_TO_SINGLE
и один обязательный format_settings; форма/DTO/API требуют явный выбор CSV либо XML.

Готовность: пользователь создаёт/редактирует определения; UI не обещает расчёт,
пока следующий срез не подключён. Unsupported definitions отклоняются явно.

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

Подключены только price.regular, price.sale (действующая на as_of), price.effective,
product.sku и product.id выбранной позиции. Закупка и категории пока не подключены.
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
Подключение закупки/категорий, publication resolver, экспорт и история — следующие срезы.

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

#### **16.6.2. Полное разрешение предложения и постоянные проекции — далее**

Set/ResetOverride через Domain, динамические STRING/TEXT/MONEY поля, fallback,
FieldValueResolver/PublicationResolver, readiness и общий preview. Затем —
материализованные проекции с реальными версиями Feed/Publication, fingerprint/
инвалидацией источников, valid_until и условным upsert без N+1. Пассивный Catalog
revision сам по себе недостаточен для актуальности. Схемные ревизии/публикация
схемы проектируются отдельно и не становятся фиктивными версиями этого среза.

### **16.7. Export Engine**

Поведение уже созданного Domain генерации и задачи, staging/serializers/ArtifactStorage, as_of,
сохранённые Product Mode/числовые константы формулы, source revisions, engine version, lease/heartbeat/
fencing/retry, counts/issues/history и условная активация одного артефакта.
VARIABLE_TO_SINGLE создаёт одну плоскую запись на выбранную публикацию в заданном
CSV либо XML, без родительских строк/группировки и повторного раскрытия Catalog.

Готовность: один файл согласно снимку format_settings, старый/ошибочный результат
не заменяет активный, retry сохраняет формат/параметры и временной контекст и определение формулы.

### **16.8. Public Distribution**

Public registry/admission, поведение FeedAccessKey и его Application-сценарии,
отдельные access_key controller/depends и public controller,
ETag/Last-Modified, streaming без DB-транзакции, отзыв/ротация и экспортный экран.

Готовность: постоянные HTTPS URL, проверка ключа/tenant и сохранение старой выдачи.

### **16.9. Stabilization**

Integration/E2E/нагрузка/security, конкуренция, AST limits, права/derived data,
время акций, смена формулы с пользовательским курсом во время запуска, восстановление задач/cleanup,
мобильный/доступный UI, observability и весь архитектурный перечень.

Готовность: критерии раздела 18 и соответствующие проверки выполнены;
нет известных нарушений слоёв/контрактов/изоляции. Пресеты — отдельное расширение.

## **17. Расширения после MVP**

| Возможность | Подготовленный механизм |
| --- | --- |
| Пресеты Prom/Rozetka/пользовательские | Исходные definition полей/AST/bindings с новыми ID при применении |
| Специфические форматы площадок | Отдельные FormatProfile/Serializer по актуальным официальным контрактам |
| Категории поддерева | Явная операция + snapshot дерева от владельца, без скрытых предков |
| Другие параметры/характеристики/бренд | ParameterRegistry с типами/правами и публичный owner reader |
| Другие стратегии закупки | Явные варианты PurchasePriceSource, без смешивания с себестоимостью |
| Межполевые выражения | Отдельный граф зависимостей и проверка циклов перед publish |
| Вложенные объекты/массивы/изображения | kind/children/item_schema, media types |
| Группировка вариантов и представление семейств | Новые значения FeedProductMode, явные правила родительских записей/групповых ID и профили форматов |
| AI/переводы | ai_instruction + locale, отдельный suggestion use case |
| Динамический ассортимент | SelectionPolicy и соответствующий Application Engine |
| Расписание/событийная перегенерация | Создание обычного Generation Request внешним планировщиком |
| Bulk overrides | Отдельный Application сценарий с optimistic locking |
| Строгий snapshot всего источника | Согласованные immutable source snapshots, не только revision ledger |
| Миграция смысла поля | Явный перенос несовместимых overrides с preview/проверками |
| Совместное использование правил вне Feed | Новый явный публичный контракт, если появится такой сценарий |

Плоская выгрузка простых товаров/выбранных вариантов в VARIABLE_TO_SINGLE,
условия по категориям, арифметика на regular/sale/purchase и явный пересчёт пользовательской формулой
уже входят в целевой MVP, а не откладываются как зависимость от другого модуля.
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
6. Нет evaluator, методов редактора полей/публикации схемы/генерации или событий.
   Unit-тесты Domain не требуют БД или HTTP; Feed CRUD имеет отдельные проверки.

#### **18.1.1. Текущий объектный срез**

1. FeedPublication, FeedGeneration, FeedAccessKey и зависимый FeedArtifact имеют
   исходно имели только create/restore; FeedPublication получил поведение и
   версию в 18.1.6. Каждый VO находится в отдельном файле.
2. SIMPLE/выбранный VARIANT представлены ссылкой, overrides типизированы,
   уникальны по field_id и не зависят от загрузки текущей схемы при restore.
3. Генерация содержит полный неизменяемый снимок одного CSV/XML без ревизий;
   статус согласован с попыткой, контекстом, датами, счётчиками, ошибкой и файлом.
4. Числовые константы и as_of хранятся точно и неизменяемо; успех не подменяет активацию файла.
5. Ключ — отдельный агрегат, хранит только 32-байтовый digest, а статус
   соответствует дате отзыва. Выпуск/проверка секрета пока не реализуются.
6. Тесты всех объектов и архитектурных границ проходят без БД/HTTP/часов/UUID
   внутри Domain. Существующий контракт Feed сохранён.

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
6. Нет ревизий, публикации схемы или генерации. Участие товаров добавлено в 18.1.6.
   Формулы и тестовый выбор товара для расчёта добавлены срезом 18.1.5.

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
7. Закупка, категории, автоматическая конвертация валют и FX не подключены.

#### **18.1.6. Реализованное управление ассортиментом**

1. Простые товары и выбранные варианты сохраняются отдельными FeedPublication.
2. Пакет до 100 атомарен, повтор/конкуренция сохраняют ID/status/overrides.
3. Пауза/возобновление/архивация/явный возврат выполняются через корень и CAS.
4. Конструктор схемы/формулы и Feed.version от изменения состава не меняются.
5. Console поддерживает URL/reload, серверный поиск/пагинацию, выбор между
   страницами, фиксированный снимок вариантов, 409/pending/контекст и mobile.
6. Проверка цены использует сохранённую схему и существующий evaluator без записи.
7. Архив Feed read-only, удалённый источник виден как недоступный без потери связи.
8. Полный resolver, manual overrides/readiness и постоянные проекции — далее.

### **18.2. Полный целевой MVP после последующих срезов**

1. Пользователь создаёт пустой Feed и сам задаёт поля/порядок/экспорт.
2. Текстовые поля имеют независимые locale/fallback, MONEY — необязательные валютные метки результата.
3. В MONEY выбираются source/manual/calculated, необязательная валютная метка, ELSE и
   упорядоченные IF-правила категории/других зарегистрированных параметров.
4. Формулы используют regular/sale/effective/purchase, операции и разрешённые
   функции. Закупочный источник выбран явно и проверен по tenant/правам.
5. Preview показывает первую совпавшую ветвь/ELSE, разрешённые данные и errors
   по field/rule/path. Нет скрытой подстановки отсутствия нулём/другой ценой.
6. Приоритет manual исключает повторную наценку/формулу; reset возвращает
   автоматическое определение, остальные поля не затрагиваются.
7. Схема публикуется неизменяемой версией; изменение draft не меняет текущую выдачу.
8. Привязка простых товаров и выбранных вариантов идемпотентна по паре ID;
   выбор только белого топика даёт одну публикацию, родитель и остальные варианты
   не экспортируются. Новые варианты не подключаются автоматически. Проекции
   учитывают категории/закупку/числовые формулы/версии/время акции и используемые ревизии
   позиции/родителя; устаревание видно пользователю.
9. После устранения blocking issues ENABLED-позиции готовы; Generation создаёт
   один выбранный Generic CSV либо XML из staging, с фиксированным format_settings,
   product_mode/as_of/engine version и числовыми константами формулы. VARIABLE_TO_SINGLE даёт по одной
   самостоятельной записи на публикацию, без строки VARIABLE и группировки;
   схема полей общая для SIMPLE/VARIANT.
10. Источники сохраняют собственные цены: FeedBuilder их не изменяет и не требует
    отдельного модуля прайс-листов/наценок.
11. Успех и активация разделены, активен один артефакт. Старый worker или
    несовместимая версия не заменяет новый активный результат.
12. Ошибочный запуск сохраняет предыдущую выдачу, retry/fencing/cleanup корректны.
13. Ключи/tenant/protected inputs/trace/публичные файлы защищены, cache не обходит отзыв.
14. Пройдены Domain/Integration/E2E/нагрузочные и frontend проверки, архитектурный
    перечень и stabilization. Пресеты и площадочные профили остаются будущими срезами.

**Итоговый поток:**

```text
Выбранные SIMPLE/VARIANT Catalog + нужный контекст родителей + закупочный источник
  + числовые параметры + as_of
  → Feed.export_settings.product_mode = VARIABLE_TO_SINGLE
  → FeedSchema: общие поля и AST каждого денежного расчёта
  → FeedPublication override либо IF/ELSE/expression
  → transforms / Decimal rounding / constraints
  → ResolvedPublication
  → одна плоская ExportRecord на публикацию + FormatProfile + staging
  → FeedGeneration → один CSV либо XML artifact
  → атомарная активная выдача
```

Domain моделирует и проверяет бизнес-смысл; Application получает входы и
координирует процессы; Infrastructure хранит/читает/сериализует; Presentation
предоставляет API и конструктор. Первый шаг — только правильные Domain-объекты
Feed, а не реализация всего описанного жизненного цикла сразу.
