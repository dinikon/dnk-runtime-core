# **FeedBuilder — финальный целевой план реализации**

**Архитектура:** DDD + Clean Architecture\
**Backend:** Python, FastAPI, SQLAlchemy Async, PostgreSQL\
**Frontend:** Vue 3, TypeScript, TanStack Vue Query\
**Определения:** версионируемые JSONB-схемы с типизированными условиями и AST\
**Целевой MVP:** Generic CSV/XML, плоская выгрузка простых товаров и выбранных вариантов, расчёт денежных полей внутри Feed

Документ фиксирует согласованную целевую модель и последовательность реализации.
Все поля пользовательские и равноправные; обычный Feed начинается с пустой схемы.
Наценки/условия/формулы находятся в определении конкретного денежного поля.
Первый срез — только объекты Domain Feed с create/restore; остальные разделы
описывают будущие срезы. Этот план не означает наличие реализованного модуля.

## **1. Цель, границы и порядок реализации**

FeedBuilder — самостоятельный bounded context, создающий пользовательские
выгрузки из Catalog и других разрешённых источников. Условия и формулы цены
принадлежат денежному полю конкретной схемы Feed. Отдельный модуль прайс-листов
или наценок для работы FeedBuilder не требуется.

### **1.1. Целевые возможности MVP**

1. Создать Feed с названием, кодом и пустой пользовательской схемой.
2. Собрать структуру предложения из произвольного числа STRING, TEXT и MONEY полей.
3. Выбрать каждому полю источник или ручное заполнение, язык/валюту,
   ограничения, преобразования и экспортное имя.
4. Для MONEY выбрать прямой источник либо условный расчёт с формулой по умолчанию.
5. Задать IF/ELSE IF правила по категориям и другим зарегистрированным параметрам
   товара, используя обычную, акционную и явно определённую закупочную цену.
6. Привязать простые товары и выбранные варианты Catalog, просматривать значения/ошибки
   и задавать независимые overrides каждой позиции.
7. Сохранять draft, публиковать неизменяемую версию схемы и проверять preview.
8. Асинхронно генерировать Generic CSV/XML из одного проверенного набора записей.
9. Получать файлы по постоянным HTTPS-ссылкам; ошибочная генерация сохраняет прежнюю выдачу.

| Тип поля | Значение | Контекст |
| --- | --- | --- |
| STRING | str | Локализованный или языконезависимый текст |
| TEXT | str | Описание и длинный текст |
| MONEY | MoneyVO с Decimal на выходе | Валюта поля, источник или формула |

Мультиязычность и мультивалютность задаются полям, не всему Feed. Денежная формула
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
  локалью или целевой валютой: создаётся новое поле либо отдельная будущая миграция.
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

### **1.4. Границы контекстов**

```text
Catalog: простые товары, родители/варианты, эффективный контент, regular/sale price, категории и ревизии
Supplier Sourcing: явно выбранное закупочное предложение
Currency: неизменяемый FX snapshot
reference_data: поддерживаемые коды локалей и валют
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
| Корни агрегатов целевого модуля | Feed, FeedPublication, FeedGeneration |
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
| Как создаются файлы | Асинхронно, все выбранные форматы из одного staging; по умолчанию CSV и XML |
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
   поля/правила не получают самостоятельных repositories. Первый срез содержит
   только domain/feed и применимые тесты, без пустых заготовок других слоёв.
2. Domain — обычный Python без FastAPI, Pydantic, SQLAlchemy, I/O и logger.
   Фабрики агрегата/Entity create/restore явные; __post_init__ допустим только VO.
   В первом срезе других методов поведения нет. В последующих срезах состояние
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
8. Application получает данные Catalog, категорий, закупочных источников, курсов
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
  domain/{feed,publication,generation}/
  application/{feed,publication,generation}/
    command/<scenario>/{command.py,handler.py,dto.py}
    query/<scenario>/{query.py,handler.py,dto.py}
    port/
  application/service/
  infrastructure/{feed,publication,generation}/persistence/
  infrastructure/persistence/models/<table>.py
  infrastructure/{catalog,supplier_sourcing,currency,storage,serialization}/
  presentation/{feed,publication,generation}/
    router.py, depends.py
    http/{controller,request,response}/<scenario>.py
  presentation/depends/
```

Первый срез создаёт только файлы Domain, перечисленные в разделе 3.4.
Остальные каталоги появляются по факту реализации. Общие UoW/jobs/events/storage
механизмы переиспользуются; файловая структура не определяет границы агрегатов.

## **3. Domain: объекты первого среза и будущие границы**

### **3.1. Aggregate Roots целевого модуля**

| Корень | Ответственность | Когда реализуется |
| --- | --- | --- |
| Feed | Определения полей, расчётов и настройки схемы/экспорта | Объекты — первый срез; поведение — следующие |
| FeedPublication | Привязка товара, участие, индивидуальные overrides | После Domain Feed |
| FeedGeneration | Выполнение, snapshot контекста, issues и артефакты | Экспортный срез |

FieldDefinition и ConditionalPriceRule — Entity внутри Feed. Отдельного корня
для наценок нет. FeedSchemaVO и настройки — VO. Проекция публикации — read model.
Связи самостоятельных агрегатов — по ID, не через Python-ссылки на чужой агрегат.

### **3.2. Feed: состояние и фабрики первого среза**

| Поле | Тип / смысл |
| --- | --- |
| id | FeedIdVO |
| name, code | FeedNameVO, FeedCodeVO |
| status | FeedStatus: DRAFT / ACTIVE / PAUSED / ARCHIVED, пока без переходов |
| schema | FeedSchemaVO; допускает пустой состав |
| export_settings | FeedExportSettingsVO |
| created_at, updated_at | Timezone-aware datetime |

Feed.create получает явные ID/время и исходные настройки, создаёт пустую схему,
если состав не передан. Feed.restore восстанавливает все переданные значения,
проверяет согласованность и не генерирует ID, события или предзаполненные поля.
Новый Feed создаётся в DRAFT. Restore сохраняет явно переданное допустимое состояние.

FeedExportSettingsVO содержит product_mode: FeedProductMode с единственным
значением VARIABLE_TO_SINGLE по умолчанию, formats: tuple[ExportFormatSettings, ...]
и validation_policy. ExportFormatSettings — закрытое объединение
`CsvExportSettingsVO | XmlExportSettingsVO` в types.py. Отдельных свойств csv/xml
у FeedExportSettingsVO нет: настройки находятся только внутри выбранных элементов.

Каждый VO хранится в своём файле и определяет фиксированный формат класса:

| VO | ClassVar format | Собственные параметры |
| --- | --- | --- |
| CsvExportSettingsVO | ExportFormat.CSV | delimiter, encoding, include_header |
| XmlExportSettingsVO | ExportFormat.XML | root_name: ExportNameVO, item_name: ExportNameVO, encoding |

format не является полем конструктора; нельзя задать XML для CSV-настроек или
наоборот. Каждый VO проверяет только собственные параметры. formats принимает
непустую коллекцию из одного или двух поддержанных VO, копирует входной list в tuple
и сохраняет порядок. Пустой состав, Enum/строки/dict вместо VO и повтор формата
отклоняются; два CSV с разными delimiter тоже считаются дубликатом по format.
По умолчанию создаются `(CsvExportSettingsVO(), XmlExportSettingsVO())` с обычными
параметрами. Один элемент означает один файл, два — CSV и XML. Настройки
невыбранного формата не создаются как параллельное свойство Feed.

```python
FeedExportSettingsVO(
    product_mode=FeedProductMode.VARIABLE_TO_SINGLE,
    formats=(
        CsvExportSettingsVO(delimiter=";", include_header=True),
        XmlExportSettingsVO(
            root_name=ExportNameVO("catalog"),
            item_name=ExportNameVO("product"),
        ),
    ),
)
```

FeedProductMode объявляется в отдельном enum/feed_product_mode.py:

```python
class FeedProductMode(StrEnum):
    """Определяет представление выбранных товаров в выгрузке."""

    VARIABLE_TO_SINGLE = "VARIABLE_TO_SINGLE"
```

VO проверяет в __post_init__, что product_mode — экземпляр FeedProductMode;
сырые строки, неизвестные значения и чужие Enum отклоняются с InvalidFeedValueError.
Будущая граница ввода явно преобразует код в Enum. Feed.create получает режим
из настроек либо использует настройки по умолчанию; Feed.restore сохраняет его
без изменения остальных свойств. Product Mode принадлежит настройкам экспорта
Feed, применяется ко всем его форматам и не входит в FieldDefinition/FeedSchemaVO.
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

Первый срез не добавляет внутренние методы редактирования, публикации или генерации.
Достаточно create/restore и проверок корректности конструируемого состояния.
Код уникален в пределах tenant на будущем persistence/application уровне;
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
| MoneyFieldTypeVO | kind=MONEY, обязательная currency: CurrencyVO, value_definition: MoneyValueDefinitionVO, constraints: MoneyConstraintsVO, transforms: tuple[TransformDefinitionVO, ...] |

kind — фиксированная ClassVar класса VO, не вход конструктора и не отдельный
изменяемый enum поля. Например, SKU — StringFieldTypeVO с locale=None;
локализованный заголовок — StringFieldTypeVO с locale; описание — TextFieldTypeVO;
цена — MoneyFieldTypeVO с currency. Ключ не определяет тип или доступные настройки.
У текстовых VO нет currency, у денежного — locale/fallback_policy.

TextValueDefinition — объединение SourceValueDefinitionVO и ManualValueDefinitionVO:

- SourceValueDefinitionVO: kind=SOURCE, source: SourceReferenceVO. Для STRING/TEXT.
- ManualValueDefinitionVO: kind=MANUAL. Для STRING/TEXT без автоматического источника.
- MoneyValueDefinitionVO: kind=MONEY, mode=SOURCE / CALCULATED / MANUAL.
  Принадлежит MoneyFieldTypeVO; содержит либо source, либо calculation, либо ни того
  ни другого для ручного ввода. Два автоматических способа одновременно запрещены.

У MONEY целевая валюта обязательна. Для локализованного источника текста нужна
locale; для языконезависимого текста допускается None. Форма locale/currency
проверяется VO, поддержка кодов и языковые требования внешнего источника — будущим
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
| REGULAR_PRICE | item.regular_price | Обычная цена с валютой |

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
проверяются в следующих срезах через SourcePathRegistry/Application; Domain
источники не читает. Новый встроенный путь/провайдер требует явного расширения
Enum и проверки допустимой пары; пользователь не регистрирует произвольный path.
Для будущих пользовательских характеристик вводится отдельная типизированная
ссылка по ID характеристики в соответствующем срезе.

PriceCalculationVO содержит calculation_currency, упорядоченный
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
    money_literal.py                 MoneyLiteralVO
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

CurrencyVO и MoneyVO переиспользуются из shared; FeedIdVO/FieldIdVO/PriceRuleIdVO
строятся на существующем EntityIdVO. Новый LocaleCodeVO локален FeedBuilder и
не импортирует внутренний LocaleVO/ошибки Catalog. DTO, repository, events,
policies исполнения и evaluator пока не создаются. types.py не объединяет
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

MoneyVO хранит итоговую сумму/валюту, не формулы. Исходная цена Catalog допускает
до 6 дробных знаков, shared MoneyVO — 4. Поэтому будущий evaluator использует
точные Decimal с валютой без раннего приведения к MoneyVO. Приведение до 4 знаков
и валютное/полевое округление задаются явно на финальном шаге; финансовый контекст
не зависит от ambient Decimal context. Float нигде не используется.

### **3.6. Состояние Feed в последующих срезах**

При реализации редактирования/публикации schema первого среза станет рабочим
определением draft. Добавятся ссылка на текущую неизменяемую опубликованную
версию, draft revision/base version, configuration_version, persistence version,
счётчик запросов и ссылка на активную генерацию вместе с её sequence.
Структура FieldDefinition и PriceCalculationVO при этом сохраняется.
История схем целиком не загружается в агрегат.

Будущие domain-операции владеют изменениями полей/правил и публикацией;
ни Application, ни дочерний объект не обходят корень. Конкретные методы
добавляются вместе с поведением соответствующего среза, не заготовками сейчас.
FeedGeneration/FeedPublication также получают собственные create/restore и методы
только в своих срезах. row_version не означает commit Domain.

Жизненный цикл следующего среза: первая публикация переводит DRAFT в ACTIVE;
ACTIVE можно приостановить и затем возобновить через PAUSED. Новая публикация
у PAUSED не возобновляет генерации автоматически. ARCHIVED — конечное состояние,
из него редактирование/генерация не разрешены. Пауза сохраняет прежнюю публичную
выдачу, архивация отключает public route в общей транзакции и сохраняет историю.
UpdateFeedSettings передаёт желаемый status, переход проверяет Domain.

### **3.7. Будущая FeedPublication и готовность**

Publication хранит id, feed_id, catalog_item_id, catalog_variant_id,
status, overrides по field_id, version и timestamps. Ссылка на Catalog однозначна:

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

PublicationStatus: DRAFT / ENABLED / PAUSED / ARCHIVED.
Readiness: READY / NEEDS_INPUT / INVALID / STALE. Это разные измерения.

- NEEDS_INPUT: нет обязательного ручного/текстового значения, перевода либо
  MANUAL_REQUIRED требует ручного перевода, при отсутствии более серьёзных ошибок.
- INVALID: ошибка вычисления, нужного параметра/курса, типа, валюты, transform
  или constraints. Необязательность поля не скрывает ошибку выбранного расчёта.
- READY: нет блокирующих issues, обязательные значения корректны.
- STALE: сохранённая проекция устарела; не результат текущего вычисления.

Источник технически недоступен — отдельный сбой зависимости, не пустое значение.
Валидный override не требует получения параметров/курсов для автоматического
расчёта этого поля. С STRICT ошибка ENABLED-публикации блокирует весь новый файл;
молчаливое исключение товаров запрещено.

### **3.8. Будущая FeedGeneration**

Фиксирует id, feed_id, schema_version, configuration_version, request_sequence,
as_of, fx_rate_snapshot_id, export_settings_snapshot, calculation_engine_version,
attempt_token/lease, статусы PENDING → RUNNING → SUCCEEDED / FAILED,
счётчики, issues и артефакты. Engine version — версия семантики интерпретатора,
не отдельная ценовая политика; старые определения не переинтерпретируются молча.

Успех генерации и активация — разные действия. Изменившаяся схема/конфигурация
или более новая активная sequence препятствуют активации старого результата.
Повтор использует прежние as_of/FX/схему, новая конфигурация требует нового задания.

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
              "calculation_currency": "UAH",
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
| type_definition.currency | Только MONEY, обязательная целевая валюта |
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
- Конечный тип формулы MONEY, выбранные валюта вычисления и денежные константы.
- Известные операции, функции и точные схемы их параметров; обязательный ELSE.
- Допустимость операций для коллекций, денег, чисел, UUID/строк/boolean.
- Поддержка локалей/валют и прав на источник через справочники/Application Ports.
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

**Draft хранится отдельно от опубликованных версий.** Это упрощает редактирование, блокировки и обеспечение неизменяемости опубликованной конфигурации. Все SQL-фрагменты ниже задают целевую структуру и реализуются tenant-миграциями Alembic с SQLAlchemy-моделями, mapper и репозиториями.

### **5.2. Таблица Feed**

```
CREATE TABLE fb_feeds (
    id UUID PRIMARY KEY,

    name TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE,

    configuration_version BIGINT NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN (
            'DRAFT', 'ACTIVE', 'PAUSED', 'ARCHIVED'
        )),

    active_schema_version INTEGER NULL,
    active_generation_id UUID NULL,
    active_generation_sequence BIGINT NULL,

    generation_sequence BIGINT NOT NULL DEFAULT 0,
    row_version BIGINT NOT NULL DEFAULT 1,

    export_settings JSONB NOT NULL DEFAULT '{}',

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

```

`export_settings` в MVP хранит параметры:

```json
{
  "product_mode": "VARIABLE_TO_SINGLE",
  "formats": [
    {
      "format": "csv",
      "delimiter": ",",
      "encoding": "utf-8",
      "include_header": true
    },
    {
      "format": "xml",
      "root_name": "catalog",
      "item_name": "product",
      "encoding": "utf-8"
    }
  ],
  "validation_policy": "STRICT"
}
```

Для первого релиза `STRICT` — единственная политика: нельзя опубликовать новый файл с ошибочными товарами.
product_mode хранится в том же JSONB; отдельная колонка/таблица режима не нужна.
При создании отсутствие режима во входных настройках даёт VARIABLE_TO_SINGLE;
после применения типизированных defaults запись сохраняет полный снимок настроек
с явным product_mode и структурированным массивом formats. Mapper преобразует
код product_mode в FeedProductMode, а дискриминатор formats[].format выбирает
CsvExportSettingsVO/XmlExportSettingsVO; format не передаётся в конструктор VO.
При записи mapper явно берёт format.value из ClassVar и собственные параметры
элемента: обычный dataclass asdict не добавляет ClassVar автоматически.
Готовые настройки передаются фабрике restore; бизнес-правила проверяет Domain.
Старая плоская форма formats=["csv", "xml"] с отдельными csv/xml не поддерживается;
persistence/API срезы ещё не реализованы, адаптеры совместимости заранее не вводятся.
Определение режима не меняет schema_format_version. В будущих срезах изменение
настроек экспорта учитывается configuration_version, отдельно от версии схемы.

### **5.3. Таблицы Schema**

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

### **5.4. FeedPublication**

```
CREATE TABLE fb_publications (
    id UUID PRIMARY KEY,

    feed_id UUID NOT NULL
        REFERENCES fb_feeds(id),

    catalog_item_id UUID NOT NULL,
    catalog_variant_id UUID NULL
        CHECK (catalog_variant_id IS NULL OR catalog_variant_id <> catalog_item_id),

    status TEXT NOT NULL DEFAULT 'ENABLED'
        CHECK (status IN (
            'DRAFT', 'ENABLED',
            'PAUSED', 'ARCHIVED'
        )),

    overrides JSONB NOT NULL DEFAULT '{}'
        CHECK (jsonb_typeof(overrides) = 'object'),

    row_version BIGINT NOT NULL DEFAULT 1,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE NULLS NOT DISTINCT (
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
      "amount": "650.00",
      "currency": "UAH"
    }
  }
}

```

Если поле наследуется, запись в `overrides` не требуется.

В будущем `FieldOverride` может поддерживать дополнительные режимы: `CLEAR`, `EXPRESSION`, `GENERATED`, не меняя физическую модель.

### **5.5. Материализованная проекция**

```
CREATE TABLE fb_publication_projections (
    publication_id UUID PRIMARY KEY
        REFERENCES fb_publications(id),

    schema_version INTEGER NOT NULL,
    publication_version BIGINT NOT NULL,

    catalog_revision TEXT NULL,
    configuration_version BIGINT NOT NULL,
    fx_rate_snapshot_id UUID NULL,
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
configuration_version, ревизий фактических источников, актуального набора FX
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

    schema_version INTEGER NOT NULL,
    configuration_version BIGINT NOT NULL,
    fx_rate_snapshot_id UUID NULL,
    fx_rate_snapshot JSONB NULL,
    as_of TIMESTAMPTZ NULL,
    calculation_engine_version INTEGER NOT NULL,
    export_settings_snapshot JSONB NOT NULL,
    request_sequence BIGINT NOT NULL,

    status TEXT NOT NULL
        CHECK (status IN (
            'PENDING', 'RUNNING',
            'SUCCEEDED', 'FAILED'
        )),

    attempt_count INTEGER NOT NULL DEFAULT 0,
    attempt_token UUID NULL,
    lease_until TIMESTAMPTZ NULL,

    total_items INTEGER NOT NULL DEFAULT 0,
    exported_items INTEGER NOT NULL DEFAULT 0,
    rejected_items INTEGER NOT NULL DEFAULT 0,

    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ NULL,
    finished_at TIMESTAMPTZ NULL,

    UNIQUE (feed_id, request_sequence),
    UNIQUE (feed_id, id),

    FOREIGN KEY (feed_id, schema_version)
        REFERENCES fb_schema_versions(feed_id, version)
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

    UNIQUE (generation_id, format_code)
);

ALTER TABLE fb_feeds
ADD CONSTRAINT fk_fb_active_generation
FOREIGN KEY (id, active_generation_id)
REFERENCES fb_generations(feed_id, id);

```

Таким образом, `Feed.active_generation_id` указывает на конкретную успешную
генерацию, а она — на все выбранные файлы: CSV, XML либо оба. Артефакты отсутствующих
в снимке форматов не входят в активный набор.

При ошибке новой генерации указатель не изменяется.

### **5.7. Доступ по URL**

```
CREATE TABLE fb_access_keys (
    id UUID PRIMARY KEY,

    feed_id UUID NOT NULL
        REFERENCES fb_feeds(id),

    token_hash BYTEA NOT NULL,

    status TEXT NOT NULL DEFAULT 'ACTIVE',

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ NULL
);

```

В `public` schema создаётся дополнительная таблица `feed_public_routes` с полями `public_id`, `tenant_id`, `feed_id`, `status`.

Она позволяет по публичному URL найти нужный tenant, не допуская прямого выбора SQL-схемы из пользовательского ввода.

### **5.8. Контекст расчёта и ревизии источников**

Правила и AST хранятся только в definition схемы. Их редактирование — обычный
SaveFeedSchemaDraft и PublishFeedSchema, без отдельных таблиц/назначений политик.
Поле schema_format_version определяет формат дерева, а calculation_engine_version
генерации — поддержанную семантику вычисления. Неподдерживаемая версия отклоняется.

В fb_publication_projections дополнительно сохраняются as_of, valid_until,
FX snapshot и source_revisions: JSONB с ревизиями фактически использованных
Catalog/категорий/закупочных источников. valid_until — ближайшая известная граница
акции/временной зависимости, если она есть; computed_at не заменяет as_of.
На границе времени проекция STALE без ожидания события изменения товара.

В staging сохраняются фактические зависимости каждой записи: item/revisions,
идентификатор выбранного закупочного предложения, нужные временные границы,
применённый rule_id и FX snapshot. Чувствительные суммы не копируются в общие логи.

Книга курсов принадлежит Currency; FeedBuilder использует публичный snapshot
контракт существующего модуля, не создаёт свой справочник. Snapshot содержит
направление котировки, валюты, точный курс, источник и время действия.
Текущая Currency-книга не является историей котировок. Поэтому генерация
сохраняет также fx_rate_snapshot JSONB с использованным набором/metadata для retry;
это снимок контекста конкретного задания, не управляемый FeedBuilder справочник.
Контекст фиксируется до первого расчёта и сохраняется для retry. Отсутствующий курс
не подставляется устаревшим/условным значением. Для полностью ручной/одновалютной
генерации FX snapshot может не требоваться.

configuration_version изменяется для влияющих на экспорт настроек Feed;
все определения полей/формул/порядка правил входят в schema_version. Row version
защищает конкурентное сохранение, не заменяет эти доменные версии.

## **6. Application: целевые порты, сценарии и транзакции**

Этот раздел реализуется после объектов и поведения Domain. В первом срезе
Application-классы, порты и репозитории не создаются.

### **6.1. Контракты хранения и внешних данных**

Write contracts FeedRepositoryProtocol, FeedPublicationRepositoryProtocol и
FeedGenerationRepositoryProtocol принадлежат Domain своих корней и работают
с агрегатами. Draft/версии/правила сохраняются через границу Feed; репозитории
для каждого VO, поля, правила или таблицы не создаются.

| Application Port / Service | Назначение |
| --- | --- |
| FeedQueryRepositoryProtocol | Списки/детали Feed и метаданные схем |
| FeedPublicationQueryRepositoryProtocol | Карточки, страницы, фильтры, статистика |
| FeedGenerationQueryRepositoryProtocol | История, issues и артефакты |
| SchemaVersionReaderProtocol | Immutable draft/опубликованные определения |
| PublicationProjectionPort | Условная запись и инвалидация проекций |
| CatalogProductReader | Batch простые позиции/выбранные варианты, принадлежность родителю, эффективный контент, regular/sale price, интервалы акций и ревизии |
| ProductParameterReaderPort | Batch зарегистрированные категории/SKU/другие параметры |
| PurchasePriceReaderPort | Batch закупочные цены по явной привязке источника |
| FxRateSnapshotPort | Чтение/фиксация единого snapshot и ревизии текущей книги |
| ReferenceDataReaderPort | Поддержка кодов локалей/валют |
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
Пакеты Catalog/Currency/Supplier Sourcing не импортируются во внутренний Domain Feed.
Если необходимого публичного чтения ещё нет, согласовать минимальный owner-контракт;
это не требует создания отдельного модуля прайс-листов.

SourcePathRegistry описывает источники из закрытого контракта Domain:
тип результата, locale, доступ и обработчик. Он не разрешает произвольные строковые
provider/path в обход SourceReferenceVO и не дублируется отдельным списком UI.
Реестр, порты и адаптеры в первом Domain-срезе не создаются.

### **6.2. Команды: входы и результаты**

Все сценарии получают доверенные tenant_id/actor_id. Каждый имеет собственные
Command, Handler и конкретный DTO результата либо None. Для существующих
объектов передаются нужные expected_version; HTTP Request/ORM не входят в контракт.

| Сценарий | Вход кроме контекста | Результат |
| --- | --- | --- |
| CreateFeed | name, code, export_settings, optional schema | CreateFeedResultDTO: feed_id, draft_version, row_version |
| UpdateFeedSettings | feed_id, изменяемые настройки, expected_version | UpdateFeedSettingsResultDTO: версии |
| SaveFeedSchemaDraft | feed_id, definition с полями/AST/bindings, expected draft version или null, expected_schema_version | SaveFeedSchemaDraftResultDTO: draft_version, issues |
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
| ListFeeds | фильтры/сортировка/пагинация | Page[FeedListItemDTO] |
| GetFeed | feed_id | FeedDetailsDTO |
| GetFeedSchema | feed_id, ACTIVE / DRAFT / version | FeedSchemaDetailsDTO |
| ListFieldTypes / ListSourcePaths / ListTransforms | контекст/тип | Собственные DTO метаданных |
| ListCalculationParameters / ListCalculationOperations | контекст/тип | Собственные DTO типов/операций/прав |
| ListFeedPublications | feed_id, фильтры/пагинация | Page[FeedPublicationListItemDTO] |
| GetFeedPublication | publication_id | FeedPublicationDetailsDTO |
| PreviewFeedPublication | publication_id, ACTIVE / DRAFT | PublicationPreviewDTO |
| PreviewFeed | feed_id, schema_mode, limit | FeedPreviewDTO |
| PreviewFieldCalculation | feed_id, catalog_item_id, catalog_variant_id или null, field_id, schema_mode, optional definition_override | FieldCalculationPreviewDTO |
| GetGeneration / ListGenerations | generation_id / feed_id и пагинация | GenerationDetailsDTO / Page[GenerationListItemDTO] |
| ListGenerationIssues | generation_id, фильтры/пагинация | Page[GenerationIssueDTO] |
| GetActiveFeedArtifact | feed_id, format | ActiveFeedArtifactDTO |
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

schema_version включает условия, AST, валюты расчёта и закупочные bindings.
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
| price.regular | Обычная продажная цена с валютой |
| price.sale | Действующая акционная цена на as_of, либо отсутствие |
| price.effective | Sale при действующей акции, иначе regular |
| price.purchase | Закупочная цена из явного purchase_source |
| product.category_ids | Набор явно назначенных UUID категорий |
| product.sku / product.id | SKU / идентификатор товара |

Это целевой потребительский контракт FeedBuilder, а не утверждение о готовом API.
Четыре прямых источника Catalog соответствуют SourceProvider.CATALOG и
CatalogSourcePath. Коды price.* и product.* в таблице — отдельные параметры AST,
а не дополнительные значения CatalogSourcePath; ParameterReferenceVO в этом
срезе не меняется и проверяет форму ID, семантику задаёт будущий ParameterRegistryPort.
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
configuration_version, as_of, calculation_engine_version, FX snapshot и generation_id
при экспорте. Локаль берётся из StringFieldTypeVO/TextFieldTypeVO, целевая валюта —
из MoneyFieldTypeVO; calculation_currency принадлежит PriceCalculationVO.
ID выбранной позиции выводится из пары: catalog_variant_id, если он задан,
иначе catalog_item_id; отдельной изменяемой настройки выбранного ID нет.
Тип определяется классом type_definition/kind без отдельного поля value_type.
Один context используется preview/resolve/serializer без скрытого чтения часов.

ResolvedField: field_id/key/type, source_value при необходимости, override_value,
resolved_value, origin=INHERITED / CALCULATED / MANUAL, issues, actual_locale,
валюта, использованные source revisions и безопасный calculation trace.
Fallback отмечается явно в actual_locale/метаданных, не отдельным скрытым источником.

### **7.4. Последовательность FieldValueResolver**

1. Если есть override — взять ручное значение; автоматическое определение для
   итогового результата не исполняется. Иначе перейти к type_definition.value_definition.
2. MANUAL без override — отсутствующее значение. SOURCE — получить источник.
   Для MONEY SOURCE при необходимости конвертировать в валюту поля через общий FX context.
3. CALCULATED — собрать snapshot разрешённых параметров, выбрать правило/ELSE
   и вызвать чистый evaluator по правилам раздела 8.
4. Parse/проверка типа и валюты; apply type_definition.transforms в порядке схемы.
5. Явное финальное округление/приведение к MoneyVO, затем type_definition.constraints.
6. Вернуть значение/origin/trace/issues; PublicationResolver собирает readiness.

Валидный manual MONEY должен уже иметь валюту поля: иначе CURRENCY_MISMATCH,
без скрытой конвертации или повторной наценки. Для диагностического сравнения
preview может дополнительно читать источник; сбой такого необязательного чтения
не делает корректный override ошибочным.

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
должны учитывать точность shared MoneyVO и выбранную валюту.

### **7.7. PublicationResolver и актуальность**

Snapshot товара и параметры читаются пакетно для всех нужных полей/локалей.
Идентичные зависимости можно кешировать в рамках контекста; key включает tenant,
пару item/variant IDs, фактические source revisions, определение, валюты, as_of и FX.
Кеши соседних вариантов не смешиваются; родительская revision учитывается при
наследовании. Разные поля могут иметь разные
формулы; общей наценки Feed поверх результата не существует.

Проекция хранит версии схемы/публикации/конфигурации, source revisions, as_of,
valid_until и FX. При условном upsert старый worker не перезаписывает новый.
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
содержит PriceCalculationVO: calculation_currency, rules, default_expression
и optional purchase_source при зависимости price.purchase. Процент/фиксированная
надбавка в UI — удобный способ построить выражение конечной цены.
Самостоятельный объект MoneyVO по-прежнему содержит только сумму/валюту.

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
| GT / GTE / LT / LTE | Упорядоченное сравнение чисел или денег |
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
| Фиксированная надбавка | price.regular + Money(50, UAH) |
| −5% от акционной | price.sale × 0.95 |
| Цена не ниже закупки с наценкой | max(price.sale, price.purchase × 1.15) |
| Маржа 25% от закупки | price.purchase / (1 − 0.25) |

Все примеры имеют конечный тип MONEY; функция max не подменяет отсутствующую
sale price — соответствующий пример требует EXISTS или явной ветви ELSE.
Значение «20» в UI не угадывается как процент: операция «+20%» строит множитель 1.20.

Допустимы ADD/SUBTRACT/MULTIPLY/DIVIDE, унарный NEGATE и функции min/max/abs.
Скобки отображаются структурой AST. Деньги ± деньги дают деньги, деньги × число
и деньги / число — деньги, деньги / деньги одной валюты — число; деньги × деньги
и деньги + число запрещены. Денежная константа всегда имеет явную валюту.
Min/max работают с однородными типами; корень формулы обязан вернуть деньги.
Все нужные денежные значения сравниваются/вычисляются в calculation_currency.

AST содержит ParameterReferenceVO, DecimalLiteralVO, MoneyLiteralVO,
ArithmeticExpressionVO, FunctionExpressionVO; ScalarLiteralVO нужен для UUID,
строк и boolean, CollectionLiteralVO — для конечных однородных tuples литералов
условий. Literal не исполняет код.
В JSON Decimal — строка, literal boolean — настоящий boolean, UUID проверяется явно.
Каждый вид узла и параметры имеют конкретный контракт/арность; unknown fields
или операции отклоняются. Первая версия не имеет циклов, пользовательских функций,
внешних вызовов и ссылок на результаты других вычисляемых полей Feed.

Канонические свойства узлов:

| kind | Свойства |
| --- | --- |
| parameter | parameter: зарегистрированный ID |
| decimal | value: конечная десятичная строка |
| money | amount: десятичная строка, currency: код |
| scalar | value_type: uuid/string/boolean, value соответствующего типа |
| collection | item_type и items одного скалярного типа |
| arithmetic | operator и left/right; для NEGATE только operand |
| function | function: MIN/MAX/ABS, arguments: массив выражений |
| comparison | operator, left, right |
| logical | operator и operands; NOT имеет ровно один |
| presence | operator: EXISTS/IS_MISSING и parameter |

MIN/MAX принимают минимум два аргумента, ABS — один. Неупомянутые альтернативные
свойства узла отсутствуют, а не игнорируются. Группы ALL/ANY непустые.

### **8.5. Валюты, точность и время**

Один as_of определяет действие всех акций. Источники денег, участвующие в
условии или выбранной формуле, приводятся к calculation_currency по одному FX
snapshot. Результат переводится в currency поля, затем transforms и явное
финальное округление до поддерживаемой точности, MoneyVO и constraints.
Для SOURCE достаточно конвертации исходной суммы в currency поля.
Ручной override уже окончателен в целевой валюте и не проходит эти расчёты.

Рабочий Decimal context фиксируется версией evaluator (начально precision=40,
ROUND_HALF_UP для деления); не зависит от настроек процесса. Промежуточные суммы
не квантуются в 4 знака на каждом узле. Финальное приведение к shared MoneyVO
(4 знака, ROUND_HALF_UP) явно отражается в trace и применяется до constraints.
Округление с шагом выполняется до этого приведения. Ограничения сложности/диапазона
предотвращают выход за поддерживаемые числа; недопустимый результат — issue,
а не скрытое обнуление. Отрицательность суммы проверяется constraints поля,
например min_amount=0, а не специальным именем price.

Нужный курс не заменяется условным/устаревшим. Отсутствующий курс неисполненной
ветви не блокирует результат, но сам AST всех ветвей проходит publish-проверку.
Необходимые курсы/источники могут предзагружаться batch без объявления отсутствия
неиспользованной зависимости ошибкой. Snapshot фиксирует доступные направления,
а evaluator запрашивает только реально нужные преобразования.

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
| FX_RATE_MISSING | Нет реально необходимого курса snapshot |
| NUMERIC_RANGE_EXCEEDED | Недопустимый диапазон/результат |
| CALCULATION_LIMIT_EXCEEDED | Превышен лимит исполнения |
| UNSUPPORTED_CALCULATION_VERSION | Не поддерживается семантика/формат дерева |

Issue содержит field_id, optional rule_id и path узла. Trace: выбранное правило
либо ELSE, проверенные условия, реально использованные параметры/ревизии,
конвертация, округление и конечный результат. Исходная закупочная цена и
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

Application проверяет права, получает Feed/опубликованную схему и внешние факты
о выбранных ссылках через CatalogProductReader. Domain получает типизированные
данные для проверки собственных правил публикации, без I/O; допустимость
product_mode проверяет VO настроек. В одной транзакции создаются недостающие
FeedPublication и задачи проекций; результат отображает каждую нормализованную
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

### **9.2. Установка и сброс override**

SetPublicationOverride проверяет expected_version, field_id активной схемы и
базовый входной тип, вызывает Domain публикации и сохраняет её/инвалидацию в одной
транзакции. Непарсящаяся сумма отклоняется, Decimal/валюта сохраняются явно.
Нарушение max_length/min_amount или корректно представленная неверная валюта
может сохраняться как ввод с INVALID, чтобы пользователь не терял данные.
Ручная цена окончательна: формула/наценка/конвертация источника не исполняются,
но transforms, валютная совместимость и constraints проверяются.

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

Preview ничего не публикует и не создаёт бизнес-draft. Общие as_of/FX обеспечивают
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
    """Передаёт упорядоченные ячейки публикации выбранным сериализаторам."""

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

Application проходит по export_settings_snapshot.formats, выбирает сериализатор
по фиксированному settings.format и передаёт ему соответствующий VO. CSV получает
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
- Цена сериализуется в десятичном формате без валютного символа.
- Для значений, которые могут восприниматься электронными таблицами как формулы, предусмотрена отдельная политика безопасности CSV, не искажающая машинный импорт молча.

### **10.3. XML Serializer**

XmlFeedSerializer потоково записывает XML declaration, корневой элемент,
элемент каждой публикации и теги exported cells. root_name/item_name берутся
из переданного XmlExportSettingsVO зафиксированного снимка.
Для отсутствующего необязательного значения
Generic CSV записывает пустую ячейку, Generic XML опускает элемент; профиль
может явно задать другое представление, не меняя FieldValueResolver.

`write_element()` должен экранировать спецсимволы XML и отклонять недопустимые символы XML 1.0. Имена тегов валидируются при публикации схемы.

### **10.4. Пример результата**

Пример произвольной пользовательской схемы; перечисленные поля не создаются автоматически:

```csv
title_uk,title_ru,description_uk,price_uah,price_usd
"Хлорофіл NOW Foods","Хлорофилл NOW Foods","Рідкий хлорофіл",1200.00,30.00
```

```xml
<?xml version="1.0" encoding="UTF-8"?>
<catalog>
  <product>
    <title_uk>Хлорофіл NOW Foods</title_uk>
    <title_ru>Хлорофилл NOW Foods</title_ru>
    <description_uk>Рідкий хлорофіл</description_uk>
    <price_uah>1200.00</price_uah>
    <price_usd>30.00</price_usd>
  </product>
</catalog>
```

В примере выбраны оба формата, поэтому оба файла создаются из одного набора
ExportRecord. При одном элементе formats создаётся только соответствующий файл.
Деньги сохраняют валюту в
Domain и preview; в Generic CSV/XML числовое значение не содержит символ валюты,
а назначение валюты определяется явной схемой и экспортным именем поля.

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
RequestFeedGeneration: PENDING + schema/config/export/engine versions
  → claim: RUNNING, attempt_token, lease
  → однократная фиксация as_of и нужного FX-контекста
  → выбранные ENABLED-публикации SIMPLE/VARIANT по снимку Product Mode
  → batch выбранных позиций, нужного контекста родителей и разрешённых параметров
  → override либо выбор IF/ELSE и выражение → transforms → constraints
  → staging ExportRecord + фактические source revisions/trace metadata
  → файлы выбранных formats из одного staging
  → неизменяемые артефакты
  → SUCCEEDED
  → условная атомарная активация одной ссылки на весь набор
```

### **11.2. Запрос и фиксированный контекст**

В короткой общей транзакции Request проверяет Feed/опубликованную схему,
выделяет sequence через Domain и сохраняет FeedGeneration PENDING со схемой,
configuration_version, export_settings_snapshot и calculation_engine_version.
export_settings_snapshot содержит явный product_mode=VARIABLE_TO_SINGLE и полный
упорядоченный список formats с параметрами каждого выбранного формата.
Worker использует снимок задания, preview — выбранные настройки Feed;
оба вызывают общую стратегию. Retry использует сохранённый код, а не текущий
default. Изменение delimiter/имён XML/состава formats требует новой конфигурации
и задания; retry не подмешивает текущие параметры. Экспорт не раскрывает заново
список вариантов Catalog.
Будущий Domain не позволяет запрашивать генерацию DRAFT/PAUSED/ARCHIVED Feed;
активируется Feed с опубликованной непустой экспортной схемой. Правка draft
не влияет на текущую опубликованную версию и активную выдачу.

PostgreSQL может быть очередью: PENDING захватывается FOR UPDATE SKIP LOCKED,
RUNNING получает уникальный attempt_token/lease. При внешнем брокере постановка
идёт через Outbox в общей транзакции. Repo не выполняет commit.

До первого resolve фиксируются as_of и валютный контекст. Для валютных зависимостей
используется один immutable snapshot, а не текущий курс на каждую позицию.
Существующая Currency-книга хранит текущие котировки, поэтому для retry недостаточно
одного ID: используемый набор и metadata копируются в fx_rate_snapshot JSONB
самой генерации. Это исторический контекст задания, не второй справочник валют.
FX snapshot ID сохраняется как происхождение; прямой FK/чтение ORM Currency запрещены.

Первый успешный захват расчётного контекста сохраняет as_of/FX атомарно до записи
результатов. Retry использует их же. Для полностью ручных/одновалютных источников
курсы не требуются; если нужна только ветвь без конвертации, отсутствие курса
неприменённой ветви не блокирует расчёт. Проверка нужных зависимостей выполняется
в Application/evaluator по ленивой семантике, не ошибкой всех предзагруженных полей.

### **11.3. Выполнение и транзакционные границы**

Worker читает точную версию схемы/AST/закупочных bindings, не текущий draft.
Пакеты ENABLED идут в стабильном keyset-порядке, начальный размер 500.
Потребности контента/цен/категорий/закупки собираются пакетно, без N+1 по полям
и узлам. Внутри одного вычисления наценка не применяется повторно; разные поля
имеют независимые определения. Override исключает ненужные входы своего поля.

Чистый evaluator получает as_of/все доступные snapshots, не вызывает I/O. Если
нужен дополнительный вход, Application получает его в рамках зафиксированного
контекста до соответствующего чистого шага; новые курсы не подмешиваются в
зафиксированный FX snapshot. Обновлённый context требует нового задания.

При STRICT и issue у ENABLED-публикации — FAILED с issues/counts, без переключения
выдачи. Иначе все ExportRecord сначала сохраняются в staging, затем все выбранные
форматы строятся из того же набора со своими параметрами из снимка. Storage key
уникален для попытки/артефакта, сохраняются
sha256, size и content-type. Даже успешный отдельный временный формат не активируется.

Claim, heartbeat, capture context, complete и activation — короткие отдельные
UoW во внешнем worker bootstrap. Долгое чтение/расчёт/storage не держит SQL-транзакцию.
Каждая запись результата проверяет attempt_token: потерявший lease worker
не может завершить или активировать результат. Async cancellation не подавляется.

### **11.4. Активация, retry и согласованность**

Успешная генерация активируется, только если:

- она принадлежит Feed и имеет SUCCEEDED;
- все требуемые форматы сохранены и проверены;
- schema_version и configuration_version всё ещё текущие;
- Feed допускает активацию, sequence не старее уже активной;
- попытка не потеряла право завершения, публикация результата идемпотентна.

Под блокировкой Feed условно меняется один active_generation_id и его sequence.
Все выбранные форматы переключаются вместе; если выбран один, активируется один.
Невыбранный файл предыдущей генерации не остаётся частью нового активного набора.
Повтор активации того же результата — no-op.
Изменившаяся схема/настройки дают SUCCEEDED без активации с понятной причиной.
Attempt token проверяется при complete в RUNNING. Для уже сохранённого SUCCEEDED
повторную активацию может выполнить отдельный идемпотентный процесс без продления
lease завершённой попытки. После сбоя между complete/activation активацию можно повторить. Более старый
запрос не заменяет уже активный более новый; ещё не завершившийся новый запрос
сам по себе не запрещает активировать более ранний успешный результат.

FX обновился или акция завершилась после capture — это не отменяет результат
с зафиксированным as_of/FX. Следующая генерация получит новый контекст.
При ожидании долгого задания UI показывает as_of и время создания, не обещает
актуальность на момент скачивания. Автоматическая перегенерация — будущее расписание.

MVP не имеет единого transaction snapshot всех независимых источников и набора
публикаций на начало прохода. Используются данные фактически прочитанных ревизий;
они сохраняются по записи. Retry сохраняет конфигурацию/as_of/FX, но может прочитать
более новые ревизии Catalog/закупки. Полное побитовое воспроизведение из внешних
источников не обещается; CSV/XML одной попытки одинаково опираются на staging.

Временные технические сбои повторяются с лимитом/backoff, ошибки бизнес-валидации
не ретраятся автоматически. Cleanup удаляет незавершённый staging/осиротевшие файлы
по retention с проверкой активных попыток/ссылок. Counts: total_items — обработано,
rejected_items — позиции с blocking issues, exported_items — записи в полном
успешном наборе; при FAILED exported_items=0. Первый срез не реализует эти процессы.

### **11.5. Публичная раздача**

```text
https://feeds.example.com/f/{public_id}/{token}/catalog.csv
https://feeds.example.com/f/{public_id}/{token}/catalog.xml
```

Public registry разрешает public_id в доверенный tenant, Tenancy/admission
подключают tenant, FeedAccess проверяет хеш токена/отзыв, read-side находит
активный артефакт. Нет активной выдачи — 404. UoW и DB-проверки завершаются
до streaming; сессия/ORM не живут вместе с долгой HTTP-передачей файла.

Поддержать ETag, Last-Modified, Content-Type и HTTPS. Токен показывается однократно,
в SQL хранится криптографический хеш. Отзыв/ротация прекращают старый доступ;
кеш не обходит авторизацию. По умолчанию замена отзывает заменяемый ключ атомарно,
дополнительные ключи имеют независимый lifecycle. Application/access logs исключают
токен из URL. При FAILED новый файл не публикуется, старая ссылка работает.

## **12. Presentation: целевой REST API**

Маршруты ниже — контракт будущих срезов, не существующая реализация.
Все административные маршруты имеют префикс /api/feed-builder.
Controller/request/response каждого метода находятся в отдельных файлах,
router только регистрирует маршруты/статусы/Depends. HTTP DTO не входят в Domain.

### **12.1. Feed, схема и метаданные**

| Метод | Путь после префикса | Сценарий |
| --- | --- | --- |
| POST | /feeds | CreateFeed |
| GET | /feeds | ListFeeds |
| GET | /feeds/{id} | GetFeed |
| PATCH | /feeds/{id} | UpdateFeedSettings |
| GET | /feeds/{id}/schema | GetFeedSchema: ACTIVE/DRAFT/version |
| PUT | /feeds/{id}/schema/draft | SaveFeedSchemaDraft, включая AST/правила/bindings |
| POST | /feeds/{id}/schema/publish | PublishFeedSchema |
| POST | /feeds/{id}/preview | PreviewFeed |
| POST | /feeds/{id}/calculation-preview | PreviewFieldCalculation |
| GET | /field-types | ListFieldTypes |
| GET | /source-paths | ListSourcePaths |
| GET | /transforms | ListTransforms |
| GET | /calculation-parameters | ListCalculationParameters |
| GET | /calculation-operations | ListCalculationOperations |

CreateFeed принимает name/code/export_settings и optional definition; без неё
создаётся пустой draft. Поле передаёт общие свойства и type_definition с
дискриминатором kind по разделу 4. STRING/TEXT принимают locale/fallback,
MONEY — обязательную currency; неизвестные/чужие свойства отклоняются, в том числе
старые плоские value_type/locale/currency. export_settings.product_mode принимает
только VARIABLE_TO_SINGLE и по умолчанию получает это значение при создании.
GetFeed возвращает его явно; null/неизвестные коды отклоняются. Вход преобразуется
в FeedProductMode на границе до вызова Domain. PATCH различает отсутствие настройки
и явное значение, в первой версии альтернативных режимов нет.
export_settings.formats передаётся как непустой массив объектов с дискриминатором
format=csv/xml и параметрами соответствующего типа, как в разделе 5.2. Неизвестные,
чужие свойства, повторы format и старая плоская форма отклоняются. На границе
создаются нужные VO без передачи ClassVar format в конструктор. При создании без
formats используются оба VO с defaults; GET возвращает только выбранные элементы.
Для PATCH поле formats заменяет коллекцию целиком, отсутствие сохраняет её,
null/пустая коллекция недопустимы. HTTP/API классы пока не реализуются.
Схема сохраняется и возвращается в
единственной форме type_definition без параллельных aliases. Реестры /field-types
описывают возможности типов для UI и не заменяют типизированную схему параметрами
вида {name, value}. Предустановленные схемы появятся позднее через применение пресета.
ListSourcePaths выдаёт только источники из Domain-контракта с метаданными доступа
и совместимости. Входные provider/path преобразуются в Enum на границе, свободного
ввода путей нет; прямой запрос также проходит серверную проверку.

### **12.2. Публикации**

| Метод | Путь | Сценарий |
| --- | --- | --- |
| POST | /feeds/{id}/publications | AddCatalogItemsToFeed |
| GET | /feeds/{id}/publications | ListFeedPublications |
| GET | /publications/{id} | GetFeedPublication |
| DELETE | /publications/{id} | RemoveFeedPublication |
| PUT | /publications/{id}/overrides/{field_id} | SetPublicationOverride |
| DELETE | /publications/{id}/overrides/{field_id} | ResetPublicationOverride |
| PATCH | /publications/{id}/status | ChangePublicationStatus |
| POST | /publications/{id}/preview | PreviewFeedPublication |

POST /feeds/{id}/publications принимает item_references из раздела 9.1 и возвращает
mapping каждой пары catalog_item_id/catalog_variant_id в publication_id.
Простой товар передаёт null, вариант — свой ID и ID родителя. Сырой родитель VARIABLE
без выбора вариантов не создаёт публикацию. Формы/метаданные выбора используют
публичные контракты Catalog; read-запрос не добавляет позиции в Feed.

### **12.3. Генерации и ключи**

| Метод | Путь | Назначение |
| --- | --- | --- |
| POST | /feeds/{id}/generations | RequestFeedGeneration |
| GET | /feeds/{id}/generations | ListGenerations |
| GET | /generations/{id} | GetGeneration |
| GET | /generations/{id}/issues | ListGenerationIssues |
| GET | /feeds/{id}/artifacts | Активные форматы |
| POST | /feeds/{id}/access-keys | Создать ключ |
| POST | /feeds/{id}/access-keys/{key_id}/rotate | Ротация |
| DELETE | /feeds/{id}/access-keys/{key_id} | Отзыв |

### **12.4. Preview DTO и объяснение цены**

Backend возвращает publication_id, catalog_item_id/catalog_variant_id,
status/readiness, schema/config versions,
as_of, FX metadata и поля. Пример одного поля ниже: trace без разрешения на
закупочные данные, поэтому исходные защищённые суммы в нём отсутствуют.
value_type/currency здесь — производные свойства DTO результата из
FieldDefinition.type_definition.kind/currency, а не вторая копия настроек в Domain
или входная форма схемы. То же относится к типу ExportCell.

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
использованную формулу, FX и числовые шаги. Доступ только к конечной цене
не даёт автоматически доступ к исходной закупке. Политика разрешения формул
с защищёнными входами описана в разделе 14; финальная цена может сама раскрывать
производные сведения, это учитывается правами на настройку/экспорт.

### **12.5. Ошибки и версии запросов**

Transport envelope: code, message, field_id?, rule_id?, expression_path?,
details, request_id. Он не заменяет DTO успешных результатов разных use cases.
Коды включают FEED_NOT_FOUND, SCHEMA_NOT_PUBLISHED, INVALID_SCHEMA,
UNKNOWN_FIELD, UNKNOWN_SOURCE_PATH, SOURCE_TYPE_MISMATCH,
REQUIRED_VALUE_MISSING, MAX_LENGTH_EXCEEDED, CURRENCY_MISMATCH,
TRANSLATION_MANUAL_REQUIRED, VERSION_CONFLICT, SOURCE_UNAVAILABLE,
UNKNOWN_CALCULATION_PARAMETER и вычислительные коды раздела 8.6.

Запись передаёт expected_version агрегата/draft и получает новую версию;
Save draft при отсутствии использует expected_version=null с expected_schema_version.
PATCH различает отсутствие поля и null. Создание — 201, постановка задания — 202,
операция без результата — 204 без фиктивной response schema. Reset возвращает
новую версию, поэтому для него используется 200 с конкретным DTO.

Нет ресурса — 404, конфликт — 409, недопустимый ввод/definition — 422,
техническая недоступность — 503, неожиданная внутренняя ошибка — 500.
Проблемы вычисления корректного preview возвращаются в issues, а не маскируются
как транспортная ошибка. Списки/trace/preview имеют серверные лимиты и пагинацию.

## **13. Frontend: конструктор, условия и предпросмотр**

### **13.1. Создание Feed**

Форма содержит name, code и настройки форматов. В Export Settings показано
описание «Варианты как самостоятельные товары»; единственный код модели —
VARIABLE_TO_SINGLE по умолчанию. Выбор между режимами в первой версии не нужен.
DTO и чистая модель сохраняют явный код режима. Выбор форматов содержит настройки
только отмеченных CSV/XML; по умолчанию отмечены оба. Чистая модель — объединение
по format, без второго списка флагов и общих csv/xml-свойств. UI получает выбранные
настройки через props и emits изменения; API mapper собирает вложенный массив.
Backend создаёт Feed с пустым составом. Пустое состояние объясняет добавление
полей; title/description/price
не добавляются автоматически. Нет выбора общей валюты/локали вычислений или
обязательной отдельной ценовой политики.

### **13.2. Конструктор схемы**

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
  ├── ResultCurrency
  ├── ValueMode: SOURCE / CALCULATED / MANUAL
  ├── SourceSettings (SOURCE)
  ├── CalculationEditor (CALCULATED)
  │    ├── CalculationCurrency
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
хранятся Decimal-строками, денежный literal имеет валюту. Визуальный редактор
поддерживает скобки, операции и разрешённые функции; не исполняет Python/JS.
Если есть текстовое представление, оно разбирается ограниченной грамматикой в тот
же AST; при отсутствии такого parser UI остаётся визуальным. Единственный
сохраняемый источник истины — дерево, не две расходящиеся версии строки и AST.

Preview показывает выбранную ветвь/ELSE, условия, формулу, разрешённые параметры,
конвертацию, округление и результат. Ошибки привязаны к field_id/rule_id/path.
Backend исполняет арифметику; frontend может проверять форму, но не рассчитывает
вторую независимую «правильную цену». Несохранённый AST проверяется через preview
override без изменения опубликованной схемы.

### **13.4. Публикации и overrides**

Таблица: Catalog name/SKU, readiness, issues, число overrides, computed_at/STALE
и пользовательские колонки из схемы. Для основной подписи/цены нет скрытого
выбора поля по key: пользователь может выбрать колонки/основные поля отображения,
без него показываются Catalog identification и общий статус.
Пагинация/поиск/сортировка серверные, не загрузка всего Feed.

В диалоге добавления SIMPLE выбирается одной позицией, VARIABLE раскрывает список
дочерних вариантов с индивидуальными флажками и действием «Все существующие».
Выбор только белого топика отправляет только его пару ID. Снимок выбора хранится
локально до submit, query/refetch не расширяет подтверждённый набор автоматически.
После успешной mutation обновляются списки/счётчики публикаций, повторный submit
блокируется на pending; неоднозначный ответ не запускает скрытое повторное создание.
Видны родитель и выбранный вариант, но строки Feed соответствуют конкретным
публикациям, а не целым семействам. Page связывает query/mutation и UI;
компоненты выбора получают модели через props и передают выбор через emits.

Редактор получает PublicationPreviewDTO и отображает динамические поля,
source/automatic/manual/resolved, валюту/локаль и ошибки. Переключение на ручной
ввод подставляет текущее значение локально, сохраняется только явной mutation.
Reset удаляет override и возвращает автоматическое определение. У поля MANUAL
без источника отсутствие значения может дать NEEDS_INPUT. CSV/XML preview
строится на серверном результате, а не вычисляется UI.

### **13.5. Экспорт и история**

Экран показывает активную генерацию, as_of, время создания, товары/размеры,
ссылки только выбранных форматов, Generate, progress, history, issues и управление ключами.
При FAILED последнего запуска явно указано, что публичная ссылка выдаёт предыдущий
успешный набор. Изменение draft не обещает немедленную смену выгрузки.

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
- formats по умолчанию содержит CSV/XML VO. Поддерживаются только CSV, только XML
  и оба в заданном порядке; все параметры сохраняются через Feed.create/restore.
- CsvExportSettingsVO/XmlExportSettingsVO имеют фиксированный ClassVar format;
  нельзя передать противоречащий format конструктору. У FeedExportSettingsVO нет
  параллельных csv/xml-свойств. Пустая коллекция, Enum/строки/dict вместо VO,
  смешанные неверные элементы и повтор формата с разными параметрами отклоняются.
- Коллекция formats копируется в tuple; вложенные VO неизменяемы, входной список
  не меняет созданные настройки. Проверяется структурный лимит числа форматов.
- FeedProductMode содержит только VARIABLE_TO_SINGLE. FeedExportSettingsVO и
  Feed.create без явного режима используют его по умолчанию; явные настройки и
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
  и Feed.create/restore. SKU без locale допустим; currency у MONEY обязательна.
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
- Нет evaluator, методов редактирования/публикации/генерации, репозиториев,
  событий, запросов к справочникам и заготовок внешних слоёв.

Это критерии именно первого среза. Исполнение if/арифметики и full publish-проверка
не требуются до реализации соответствующих следующих срезов.

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
| Разные исходные валюты | Конвертация в calculation_currency по общему snapshot |
| Два денежных поля | Независимые формулы, без общей повторной наценки |
| Ручной override | Без формулы/конвертации, затем transforms/constraints |
| Источник имеет 6 знаков | Нет ранней потери точности, финальные 4 знака явные |
| Неподдержанный AST/версия/операция/цикл ссылок | Отклонение до выполнения |
| Превышен лимит | Структурная или CALCULATION_LIMIT_EXCEEDED ошибка |

Вычислитель проверяется чистыми fixtures snapshots/as_of/FX. Проверяется весь
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
source IDs/offer IDs/FX snapshots/артефакты. Прямого чтения чужих таблиц нет.

Проверить условную запись проекций по ревизиям/времени, valid_until на границе
акции без update-события, появление ранее отсутствующей зависимости, invalidation
по изменению AST/категории/закупочной цены/курса. EXPLAIN/query count и batch
исключают N+1 на каждый товар/поле/AST-узел.

### **15.4. Генерация и сериализация**

- Кириллица, кавычки/запятые/переносы CSV, безопасные XML-имена/escaping/символы.
- Произвольные колонки, отсутствующее необязательное значение и явная точность.
- Все выбранные форматы читают один staging, serializer не меняет цену/правила.
- Только CSV/только XML создаёт один файл с соответствующими настройками; оба
  создают два. Снимок/retry сохраняет параметры и состав formats. Невыбранный
  формат не исполняется и не публикуется.
- VARIABLE_TO_SINGLE даёт одинаковый набор самостоятельных позиций в обоих
  форматах, если выбраны оба: одна публикация — одна запись, без родителя и группировки.
  Снимок задания содержит режим, retry не подменяет его текущими настройками/defaults.
- Один as_of, фиксированный FX набор; Currency-книга обновлена — retry не читает
  новые курсы вместо сохранённого JSONB контекста.
- Изменён draft — активная схема прежняя; publish другой версии запрещает
  активацию старого результата, прежняя активная выдача сохраняется.
- Старый запрос завершился позднее нового — sequence не откатывает выдачу.
- Повтор/истёкший lease/старый attempt_token — без двойной активации.
- При выбранных CSV и XML успешен один, второй упал — весь прежний публичный
  набор сохраняется. При переходе с двух форматов на один невыбранный старый
  артефакт не выдаётся как часть нового активного набора.
- Источники недоступны технически — ограниченный retry; ошибка формулы — FAILED без retry.
- Полностью ручные поля не требуют ненужных цен/курсов.
- Отзыв/ротация ключа работают с HTTP cache; streaming не держит DB-транзакцию.
- Большой Catalog: ограниченные память/staging, keyset, heartbeat и cleanup.

### **15.5. API, UI и E2E**

```text
CreateFeed (пустая схема)
  → SaveFeedSchemaDraft (пользовательские поля, IF/ELSE/AST)
  → PreviewFieldCalculation
  → PublishFeedSchema
  → AddCatalogItemsToFeed
  → PreviewFeedPublication
  → SetPublicationOverride / ResetPublicationOverride
  → RequestFeedGeneration / ExecuteFeedGeneration
  → Download CSV/XML
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
экспорта с FeedProductMode.VARIABLE_TO_SINGLE по умолчанию и formats как tuple
CsvExportSettingsVO/XmlExportSettingsVO с фиксированными ExportFormat. По умолчанию
создаются оба VO; общих csv/xml-свойств нет.
Существующие CurrencyVO/MoneyVO/EntityIdVO
переиспользуются, чужие внутренние агрегаты не импортируются.

Не реализуются внутренние методы поведения, evaluator, policies исполнения,
events, repository, Application, SQL, API или UI. Не создаются их пустые заготовки.
Готовность: create/restore и структурные unit-тесты 15.1 проходят без внешних сервисов.

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
и структурированный массив выбранных formats с собственными параметрами.

Готовность: пользователь создаёт/редактирует определения; UI не обещает расчёт,
пока следующий срез не подключён. Unsupported definitions отклоняются явно.

### **16.5. Условия, арифметика и чтение параметров**

Чистые evaluator/типизация/лимиты/Decimal context, Application resolver,
batch простые позиции/выбранные варианты Catalog с эффективным контекстом родителей,
категории/закупка по выбранной позиции, Registry/ReferenceData, FX adapter,
PreviewFieldCalculation и объяснение ошибок/ветвей. Для закупки реализуется
явный source selector, для акции — единый as_of.

Готовность: IF/ELSE, обычная/акционная/закупочная цена, валюты и точность
проверены, ненужные ветви не исполняются, protected inputs/trace защищены.

### **16.6. Publication и проекции**

Domain публикации, явная привязка SIMPLE/выбранных VARIANT с парой ID,
фиксированный выбор «Всех существующих» без автоподключения новых вариантов,
overrides/reset, участие/readiness, FieldValueResolver/PublicationResolver,
проекции с ревизиями позиции/использованного родителя и valid_until,
список/выбор/редактор и общий preview. Доменные денежные правила не дублируются UI.

Готовность: корректный automatic/manual результат, stale на смене данных/акции,
отсутствие дублей, условный upsert и batch без N+1.

### **16.7. Export Engine**

Domain генерации и задачи, staging/serializers/ArtifactStorage, as_of,
сохранённые Product Mode/FX snapshot, source revisions, engine version, lease/heartbeat/
fencing/retry, counts/issues/history и условная активация всех форматов.
VARIABLE_TO_SINGLE создаёт одну плоскую запись на выбранную публикацию во всех
выбранных форматах, без родительских строк/группировки и повторного раскрытия Catalog.

Готовность: один либо два выбранных файла из общего staging, старый/ошибочный
результат не заменяет активный, технический retry сохраняет фиксированный
временной/валютный контекст.

### **16.8. Public Distribution**

Public registry/admission, AccessKey lifecycle, отдельный public controller,
ETag/Last-Modified, streaming без DB-транзакции, отзыв/ротация и экспортный экран.

Готовность: постоянные HTTPS URL, проверка ключа/tenant и сохранение старой выдачи.

### **16.9. Stabilization**

Integration/E2E/нагрузка/security, конкуренция, AST limits, права/derived data,
время акций, Currency refresh во время запуска, восстановление задач/cleanup,
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
условия по категориям, арифметика на regular/sale/purchase и валютная конвертация
уже входят в целевой MVP, а не откладываются как зависимость от другого модуля.
Предустановка пресета не делает поля особыми и не связывает изменение одного
Feed с другим. Схема, публикация и итоговый артефакт сохраняют отдельный смысл.

## **18. Критерии готовности**

### **18.1. Непосредственный первый срез**

1. Создаётся Feed с пустой или явно переданной пользовательской схемой.
2. Нет встроенных полей по именам и привилегированных ролей.
   Export Settings содержит единственный FeedProductMode.VARIABLE_TO_SINGLE
   по умолчанию и formats из одного/двух типизированных VO, по умолчанию обоих.
   Фабрики сохраняют режим, порядок и параметры, VO отклоняет неверные элементы
   и повторы форматов; фиксированный ExportFormat определяется классом VO.
3. Feed/FieldDefinition/ConditionalPriceRule имеют только create/restore;
   VO/enums/ошибки корректно разнесены, каждый VO — отдельный файл.
   Настройки принадлежат трём VO типов, структура расчёта проверяется
   PriceCalculationStructurePolicy без исполнения формул; уникальность — фабрикой Feed.
4. Условия, формулы, источники и настройки представлены типизированными
   неизменяемыми объектами. Неизвестный тип/некорректная структура отклоняются.
   Прямые источники ограничены SourceProvider.CATALOG и четырьмя CatalogSourcePath;
   произвольные строки и чужие Enum не принимаются.
5. Restore сохраняет идентичность, порядок и настройки без генерации новых данных.
6. Нет evaluator, методов редактирования/публикации/генерации, событий,
   репозиториев и внешних слоёв. Unit-тесты не требуют БД или HTTP.

### **18.2. Полный целевой MVP после последующих срезов**

1. Пользователь создаёт пустой Feed и сам задаёт поля/порядок/экспорт.
2. Текстовые поля имеют независимые locale/fallback, MONEY — валюты результата.
3. В MONEY выбираются source/manual/calculated, валюта вычисления, ELSE и
   упорядоченные IF-правила категории/других зарегистрированных параметров.
4. Формулы используют regular/sale/effective/purchase, операции и разрешённые
   функции. Закупочный источник выбран явно и проверен по tenant/правам.
5. Preview показывает первую совпавшую ветвь/ELSE, разрешённые данные и errors
   по field/rule/path. Нет скрытой подстановки отсутствия нулём/другой ценой.
6. Приоритет manual исключает повторную наценку/конвертацию; reset возвращает
   автоматическое определение, остальные поля не затрагиваются.
7. Схема публикуется неизменяемой версией; изменение draft не меняет текущую выдачу.
8. Привязка простых товаров и выбранных вариантов идемпотентна по паре ID;
   выбор только белого топика даёт одну публикацию, родитель и остальные варианты
   не экспортируются. Новые варианты не подключаются автоматически. Проекции
   учитывают категории/закупку/курсы/версии/время акции и используемые ревизии
   позиции/родителя; устаревание видно пользователю.
9. После устранения blocking issues ENABLED-позиции готовы; Generation создаёт
   выбранные Generic CSV/XML из одного staging, с фиксированными formats/settings,
   product_mode/as_of/FX/engine version. VARIABLE_TO_SINGLE даёт по одной
   самостоятельной записи на публикацию, без строки VARIABLE и группировки;
   схема полей общая для SIMPLE/VARIANT.
10. Источники сохраняют собственные цены: FeedBuilder их не изменяет и не требует
    отдельного модуля прайс-листов/наценок.
11. Успех и активация разделены, все форматы переключаются вместе, старый worker
    или несовместимая версия не заменяет новый активный результат.
12. Ошибочный запуск сохраняет предыдущую выдачу, retry/fencing/cleanup корректны.
13. Ключи/tenant/protected inputs/trace/публичные файлы защищены, cache не обходит отзыв.
14. Пройдены Domain/Integration/E2E/нагрузочные и frontend проверки, архитектурный
    перечень и stabilization. Пресеты и площадочные профили остаются будущими срезами.

**Итоговый поток:**

```text
Выбранные SIMPLE/VARIANT Catalog + нужный контекст родителей + закупочный источник
  + параметры + as_of + FX snapshot
  → Feed.export_settings.product_mode = VARIABLE_TO_SINGLE
  → FeedSchema: общие поля и AST каждого денежного расчёта
  → FeedPublication override либо IF/ELSE/expression
  → transforms / Decimal rounding / constraints
  → ResolvedPublication
  → одна плоская ExportRecord на публикацию + FormatProfile + staging
  → FeedGeneration → CSV/XML artifacts
  → атомарная активная выдача
```

Domain моделирует и проверяет бизнес-смысл; Application получает входы и
координирует процессы; Infrastructure хранит/читает/сериализует; Presentation
предоставляет API и конструктор. Первый шаг — только правильные Domain-объекты
Feed, а не реализация всего описанного жизненного цикла сразу.
