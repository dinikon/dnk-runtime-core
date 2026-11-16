# **Корректировка архитектуры FeedBuilder: мультиязычность, мультивалютность и наценки**

Согласен с изменением. Привязка одного языка и одной валюты к `Feed` была слишком сильным ограничением для универсального конструктора.

Предлагаю внести три принципиальных изменения:

1. **Язык определяется на уровне каждого текстового поля**, а не всего Feed.
2. **Валюта определяется на уровне каждого денежного поля**, а не всего Feed.
3. **Наценки выделяются в отдельную Pricing Policy**, привязанную к конкретному Feed, а не смешиваются с форматированием полей.

Таким образом, один Feed сможет одновременно содержать:

| Поле             | Тип    | Источник            | Дополнительные настройки |
| ---------------- | ------ | ------------------- | ------------------------ |
| `title_uk`       | STRING | Catalog.title       | `locale=uk`, max 160     |
| `title_ru`       | STRING | Catalog.title       | `locale=ru`, max 160     |
| `description_uk` | TEXT   | Catalog.description | `locale=uk`              |
| `description_ru` | TEXT   | Catalog.description | `locale=ru`              |
| `price_uah`      | MONEY  | Pricing.final_price | `currency=UAH`           |
| `price_usd`      | MONEY  | Pricing.final_price | `currency=USD`           |
| `price_eur`      | MONEY  | Pricing.final_price | `currency=EUR`           |

Каждое поле остаётся независимым: собственный `field_id`, ограничения, transforms, AI-инструкции и overrides.

Это также соответствует реальным особенностям Prom: его YML поддерживает разные поля `name`, `name_ua`, `description`, `description_ua`, а также `currencyId` для обозначения валюты цены.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://support.prom.ua\&sz=32)

Довідка для продавців+1



## **1. Исправленная архитектура модулей**

**CATALOG**

Товар, локализованный контент, базовые цены

**PRICING**

Базовая цена, PricePolicy, наценки, валютные курсы, расчет итоговой цены

**FEED BUILDER**

Схема, языковые поля, поля цен, публикации, overrides

**RESOLVED PUBLICATION**

title_uk · title_ru · price_uah · price_usd

**CSV / XML SERIALIZERS**

Экспорт с учётом требований целевого формата

### **Распределение ответственности**

| Компонент     | Что делает                                                      |
| ------------- | --------------------------------------------------------------- |
| `Catalog`     | Хранит название и описание на разных языках, текущие цены       |
| `Pricing`     | Определяет, какую цену использовать и как рассчитать наценку    |
| `Currency`    | Предоставляет валютные курсы и правила конвертации              |
| `FeedBuilder` | Определяет состав полей, языки, валюты вывода и overrides       |
| `Channels`    | Использует рассчитанные цены для API-синхронизации с площадками |

**Рекомендую считать Pricing самостоятельным bounded context**, даже если сейчас базовые цены физически хранятся в Catalog.

На первом этапе его не обязательно реализовывать как большой модуль. Достаточно `PricingPolicy`, `PriceCalculator` и адаптера чтения исходных цен.

Это особенно важно для Channels: если FeedBuilder выгрузит цену с наценкой 20%, а Channels позже синхронизирует исходную цену Catalog через API, цены начнут конфликтовать. Обе операции должны использовать одну и ту же ценовую политику.

Такой подход соответствует распространённой архитектуре commerce-систем, где ценовые политики и группы могут применяться отдельно к каналам и каталогам.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://learn.microsoft.com\&sz=32)

Microsoft Learn+1



## **2. Мультиязычная схема: изменения FieldDefinition**

Вместо `Feed.locale_code` предлагаю добавить к `FieldDefinition` необязательное свойство `locale`.

```
@dataclass(frozen=True)class FieldDefinition:    id: UUID    key: str    label: str    value_type: FieldValueType    locale: LocaleCodeVO | None    currency: CurrencyCodeVO | None    source: SourceReference | None    default_mode: ValueMode    constraints: FieldConstraints    transforms: tuple[TransformDefinition, ...]    export: FieldExportSettings    ai_instruction: str | None
```

Правила:

- `locale` разрешён для текстовых полей.
- `currency` разрешён для денежных полей.
- Для полей, не зависящих от языка, `locale=null`.
- Один Feed может содержать любое поддерживаемое количество языков и валют.
- Constraints индивидуальны для каждого поля и языка.
- Override привязан к `field_id`, поэтому украинское и русское названия можно переопределять независимо.

### **Пример схемы с переводами**

```

{
  "id": "field-title-uk",
  "key": "title_uk",
  "label": "Назва українською",
  "value_type": "string",
  "locale": "uk",
  "source": {
    "provider": "catalog",
    "path": "item.title"
  },
  "default_mode": "INHERIT",
  "constraints": {
    "required": true,
    "max_length": 160
  },
  "export": {
    "name": "name_ua"
  }
}

```

Аналогичное русскоязычное поле:

```

{
  "id": "field-title-ru",
  "key": "title_ru",
  "label": "Название на русском",
  "value_type": "string",
  "locale": "ru",
  "source": {
    "provider": "catalog",
    "path": "item.title"
  },
  "default_mode": "INHERIT",
  "constraints": {
    "required": false,
    "max_length": 160
  },
  "export": {
    "name": "name"
  }
}

```

Обрати внимание: оба поля используют один логический путь `item.title`, а язык передаётся отдельно.

Это лучше, чем кодировать язык непосредственно в строке пути:

```
item.title.uk
item.title.ru
```

Потому что теперь `SourcePathRegistry` не зависит от количества языков.

### **Псевдокод разрешения**

```
class CatalogSourceResolver:    async def resolve(        self,        source: SourceReference,        field: FieldDefinition,        context: ResolutionContext,    ) -> DomainValue:        return await self.catalog_reader.get_field(            item_id=context.catalog_item_id,            path=source.path,            locale=field.locale,        )
```

### **Отсутствующие переводы**

Необходимо добавить `fallback_policy`, чтобы система не подставляла другой язык неявно.

Например:

```
{
  "locale": "ru",
  "fallback_policy": {
    "mode": "NONE"
  }
}
```

Или:

```
{
  "locale": "ru",
  "fallback_policy": {
    "mode": "LOCALE_CHAIN",
    "locales": ["uk"]
  }
}
```

Варианты поведения:

| Политика          | Результат                                            |
| ----------------- | ---------------------------------------------------- |
| `NONE`            | Нет перевода → отсутствующее значение                |
| `LOCALE_CHAIN`    | Последовательно искать перевод на заданных языках    |
| `MANUAL_REQUIRED` | Отсутствующий перевод нужно заполнить самостоятельно |

Для торговых площадок рекомендую использовать `NONE` по умолчанию, чтобы не выгрузить украинский текст в поле русского перевода без ведома пользователя.

Для будущих AI-инструкций `locale` также становится контекстом генерации.

## **3. Мультивалютность: как должны работать денежные поля**

Предлагаю убрать единый `currency_code` из обязательных свойств Feed и сделать валюту частью определения денежного поля.

Например, один товар содержит:

```
Publication
 ├── title_uk       STRING  [uk]
 ├── title_ru       STRING  [ru]
 ├── description_uk TEXT    [uk]
 ├── description_ru TEXT    [ru]
 ├── price_uah      MONEY   [UAH]
 ├── price_usd      MONEY   [USD]
 └── price_eur      MONEY   [EUR]
```

### **Определение price_uah**

```

{
  "id": "field-price-uah",
  "key": "price_uah",
  "label": "Цена в гривне",
  "value_type": "money",
  "currency": "UAH",
  "source": {
    "provider": "pricing",
    "path": "final_price"
  },
  "default_mode": "INHERIT",
  "constraints": {
    "required": true,
    "min_amount": "0.01"
  },
  "transforms": [
    {
      "op": "money.ceil_step",
      "params": {
        "step": "1"
      }
    }
  ],
  "export": {
    "name": "price_uah"
  }
}

```

Для `price_usd` меняются только `currency`, правила округления и экспортное имя.

```
{
  "id": "field-price-usd",
  "key": "price_usd",
  "label": "Цена в долларах",
  "value_type": "money",
  "currency": "USD",
  "source": {
    "provider": "pricing",
    "path": "final_price"
  },
  "default_mode": "INHERIT",
  "constraints": {
    "required": true,
    "min_amount": "0.01"
  },
  "transforms": [
    {
      "op": "money.ceil_step",
      "params": {
        "step": "0.1"
      }
    }
  ],
  "export": {
    "name": "price_usd"
  }
}
```

### **Что важно**

Один `FeedPublication` не должен иметь одно поле `final_price`, которое принудительно выражается в валюте всего фида.

Вместо этого Pricing возвращает результаты для запрошенных валют, а FeedBuilder размещает их в отдельных полях.

Однако базовая наценка должна вычисляться **один раз по ценовой политике**, а не применяться заново при каждом валютном преобразовании.

Иначе легко получить двойную или тройную наценку.

## **4. Где должен находиться слой наценок**

В предыдущем плане отдельного PricePolicy Engine действительно не было. Были только transforms для денежного поля, например округление вверх. Но округление и коммерческая наценка — разные понятия.

Предлагаю следующую границу:

| Операция                        | Где выполняется                       |
| ------------------------------- | ------------------------------------- |
| Хранение закупочной цены        | Catalog / Supplier Sourcing / Pricing |
| Хранение базовой продажной цены | Catalog / Pricing                     |
| Выбор цены-источника            | PricingPolicy                         |
| Наценка 15%                     | Pricing Engine                        |
| Фиксированная надбавка 100 грн  | Pricing Engine                        |
| Целевая валовая маржа           | Pricing Engine                        |
| Конвертация UAH → USD           | Pricing + Currency                    |
| Дополнительная надбавка для USD | PricingPolicy                         |
| Округление до 0.1               | Field Transform                       |
| Переопределение цены товара     | FeedPublication Override              |
| Форматирование `590.30` для CSV | Serializer                            |

### **Рекомендуемое решение**

Создать в Pricing агрегат `PricePolicy` и связать его с Feed:

```
class Feed(AggregateRoot):    id: FeedId    name: str    pricing_policy_id: UUID | None    active_schema_version: int | None    ...
```

Такой подход позволяет:

- У каждого Feed иметь собственную наценку.
- Нескольким Feed использовать одну политику при необходимости.
- Централизованно изменять коммерческую ценовую стратегию.
- Применять одну политику и к FeedBuilder, и к Channels.

При этом FeedBuilder не должен напрямую изменять чужой агрегат Pricing. В UI можно разместить настройки наценки внутри Feed, но команды создания и изменения PricePolicy передавать соответствующему Application Service модуля Pricing.

### **Альтернативный вариант для первого среза**

Если отдельного Pricing пока нет, можно временно реализовать `FeedPricePolicy` внутри `FeedBuilder/domain/pricing`, соблюдая тот же контракт `PriceCalculationPort`.

Однако для полноценной CRM я рекомендую вынести его в Pricing до появления нескольких независимых способов синхронизации цен.

## **5. PricePolicy — структура агрегата**

```
class PricePolicy(AggregateRoot):    id: PricePolicyId    name: str    base_price_source: PriceSourceRef    default_rule: MarkupRule    currency_rules: tuple[CurrencyPriceRule, ...]    version: int
```

### **Основные типы наценки**

```
class MarkupType(StrEnum):    NONE = "NONE"    PERCENT = "PERCENT"    FIXED_AMOUNT = "FIXED_AMOUNT"    TARGET_MARGIN = "TARGET_MARGIN"
```

| Тип             | Формула                    |
| --------------- | -------------------------- |
| `NONE`          | \\(P = B\\)                |
| `PERCENT`       | \\(P = B \times (1 + r)\\) |
| `FIXED_AMOUNT`  | \\(P = B + A\\)            |
| `TARGET_MARGIN` | \\(P = C / (1 - m)\\)      |

Где `B` — выбранная базовая цена, `C` — себестоимость, `r` — коэффициент наценки, `A` — фиксированная сумма, `m` — целевая доля валовой маржи.

**Наценка 30% и валовая маржа 30% — не одно и то же.** Поэтому эти операции должны иметь разные типы.

Для `TARGET_MARGIN` необходимо требовать источник себестоимости; нельзя вычислять её из произвольной розничной цены. Налоги, скидки и комиссии площадок также должны иметь явную политику расчёта.

### **Пример Pricing Policy**

```

{
  "name": "Prom - основные товары",
  "base_source": {
    "provider": "catalog",
    "path": "item.regular_price"
  },
  "default_rule": {
    "type": "PERCENT",
    "value": "20"
  },
  "currency_rules": {
    "UAH": {
      "extra_markup_percent": "0"
    },
    "USD": {
      "extra_markup_percent": "5"
    }
  },
  "rounding": {
    "mode": "FIELD_DEFINED"
  }
}

```

Здесь основная наценка — 20% независимо от конечной валюты, а в USD дополнительно применяется 5% после конвертации.

Важно определить в контракте, что `currency_rules` — именно дополнительная корректировка, а не замена основной наценки. Если потребуется замена, следует использовать отдельный режим `REPLACE_DEFAULT`.

Это устранит двусмысленность в сложных коммерческих правилах.

## **6. Как задать разные наценки для разных прайс-листов**

Каждый Feed ссылается на конкретный `PricePolicy`.

| Feed                | PricePolicy        | Источник цены         | Наценка |
| ------------------- | ------------------ | --------------------- | ------- |
| Prom — основной     | `policy-prom`      | Catalog regular price | +20%    |
| Rozetka — основной  | `policy-rozetka`   | Catalog regular price | +30%    |
| Оптовый прайс       | `policy-wholesale` | Catalog regular price | +5%     |
| Прайс для партнёров | `policy-partner`   | Catalog regular price | +12%    |

Это пример четырёх независимых политик. Наценки можно изменять без редактирования всех полей схемы и без записи новой цены в Catalog.

### **Пример расчёта**

Пусть базовая цена одного товара составляет 1 000 UAH. Для демонстрации возьмём условный курс 40 UAH за 1 USD.

Один товар — два Feed

Feed: Prom

Наценка +20%

Цена UAH

# **1 200 ₴**

Цена USD

## **$30.00**

Feed: Rozetka

Наценка +30%

Цена UAH

# **1 300 ₴**

Цена USD

## **$32.50**

Пример без дополнительных валютных надбавок и налоговых корректировок; курс условный, не текущий.

Позднее можно добавить правила с разным охватом:

| Уровень         | Пример                                           |
| --------------- | ------------------------------------------------ |
| Feed            | Всем товарам +20%                                |
| Категория       | Витамины +15% вместо +20%                        |
| Товар           | Конкретному SKU +10% вместо +20%                 |
| Валюта          | Для USD дополнительная надбавка +5%              |
| Ручной Override | Установить окончательную цену конкретного товара |

Для несовместимых правил необходим явный порядок приоритета. Рекомендую **самое специфичное правило заменяет общее**, а не суммируется с ним автоматически. Дополнительные валютные корректировки применяются только тогда, когда явно задано `extra_markup`.

### **6.1. Порядок расчёта цены**

Это наиболее важный бизнес-процесс для реализации.

1\. Price Source

Получаем базовую цену с валютой

2\. Feed PricingPolicy

Применяем наценку соответствующего Feed

3\. Currency Conversion

Переводим результат в валюту конкретного поля

4\. Currency Adjustment

Применяем дополнительные валютные правила

5\. Publication Override

Если задан ручной final value — используем его вместо результата Pricing

6\. Field Transform

Округляем цену согласно настройкам поля

7\. Constraints

Проверяем тип, сумму и валюту

8\. Resolved Value

Записываем итог и происхождение значения

Ручной override применяется вместо рассчитанной цены. Поэтому наценка не должна повторно применяться к ручной цене.

Например, если `price_usd` вручную установлен как `$35`, то в экспорте будет `$35` после допустимых transforms и validation, а не `$35 + 20%`.

При этом `price_uah` может оставаться полностью наследуемым и продолжит рассчитываться из Pricing.

### **6.2. Псевдокод Pricing Engine**

```
class PriceCalculator:    def calculate_base(        self,        source_price: MoneyVO,        policy: PricePolicy,    ) -> MoneyVO:        return self.markup_engine.apply(            source_price,            policy.default_rule,        )    def calculate_targets(        self,        marked_price: MoneyVO,        policy: PricePolicy,        target_currencies: set[CurrencyCode],        rates: FxRateSnapshot,    ) -> dict[CurrencyCode, PriceQuote]:        result = {}        for currency in target_currencies:            converted = self.currency_converter.convert(                marked_price,                currency,                rates,            )            currency_rule = policy.get_currency_rule(                currency            )            adjusted = self.markup_engine.apply_extra(                converted,
```

Первоначально вызывается `calculate_base()`, затем `calculate_targets()` для всех валют, требуемых схемой.

Не нужно повторно получать исходную цену или применять основную наценку для каждого денежного поля.

### **6.3. Интеграция с FieldValueResolver**

Для обычного текстового поля используется CatalogSourceResolver.

Для денежного поля:

```
class PricingSourceResolver:    async def resolve(        self,        field: FieldDefinition,        context: ResolutionContext,    ) -> MoneyVO:        quote = await self.pricing.get_quote(            catalog_item_id=context.catalog_item_id,            pricing_policy_id=context.pricing_policy_id,            target_currency=field.currency,            calculation_context=context.price_context,        )        return quote.value
```

`PriceCalculator` отвечает за коммерческую арифметику, а `FieldValueResolver` продолжает отвечать за наследование, ручное значение, transforms и validation.

**Это позволяет не менять общую архитектуру FeedBuilder.** Меняется только источник значения денежных полей.

## **7. Изменения в SQL-моделях**

### **7.1. Feed**

Из предыдущей модели следует исключить обязательные:

```
currency_code
locale_code
```

И добавить:

```
class FeedModel:    id: UUID    name: str    pricing_policy_id: UUID | None    active_schema_version: int | None    active_generation_id: UUID | None    ...
```

Для удобства создания новых полей можно оставить `default_locale` и `default_currency`, но только как необязательные UI-настройки. Они не должны влиять на вычисление значений без явной конфигурации поля.

Набор используемых языков и валют можно определять из `FeedSchema`, например:

```
schema.used_locales()      # {"uk", "ru"}schema.used_currencies()   # {"UAH", "USD", "EUR"}
```

### **7.2. PricingPolicy и версии**

Если Pricing является отдельным bounded context:

```

CREATE TABLE pricing_policies (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,

    active_version INTEGER NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE pricing_policy_versions (
    policy_id UUID NOT NULL
        REFERENCES pricing_policies(id),

    version INTEGER NOT NULL,

    definition JSONB NOT NULL
        CHECK (jsonb_typeof(definition) = 'object'),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (policy_id, version)
);

```

Здесь `definition` содержит источник базовой цены, тип наценки, параметры и валютные корректировки.

У `fb_feeds.pricing_policy_id` будет логическая ссылка на агрегат Pricing без необходимости создавать физический FK между bounded contexts.

Если политика не назначена, явно применяется режим `NO_ADJUSTMENT`, использующий базовую цену. Не стоит делать незаметную наценку по умолчанию.

### **7.3. FeedGeneration**

В генерации необходимо фиксировать параметры, которые влияют на расчёт цены:

```
class FeedGeneration:    id: UUID    feed_id: UUID    schema_version: int    pricing_policy_id: UUID | None    pricing_policy_version: int | None    fx_rate_snapshot_id: UUID | None    status: GenerationStatus
```

В snapshot валютных курсов необходимо иметь:

- Исходную валюту.
- Целевую валюту.
- Применённый курс.
- Источник курса.
- Дату и время действия курса.

Например, для курса НБУ и ручного курса должны быть разные идентификаторы источников.

Важно: при генерации нельзя читать «текущий курс» заново для каждой товарной позиции. Используемый набор курсов фиксируется на начало выполнения, чтобы товары в одном файле не получали разные конвертации из-за обновления курса.

Сам справочник валют и курсов остаётся в Currency/Pricing, а не дублируется в FeedBuilder.

## **8. Какие изменения нужны в UI**

В существующий конструктор я бы добавил две самостоятельные зоны: **настройки цены Feed** и **локализация/валюта конкретного поля**.

**Feed Builder**

Prom — основной прайс

Schema v2

**Настройки ценообразования**

PricePolicy

Prom Retail +20%

Базовая цена

Catalog regular_price

Валютные курсы

Currency Provider

**Schema / Publication**

title_uk

STRING

uk

title_ru

STRING

ru

description_uk

TEXT

uk

description_ru

TEXT

ru

price_uah

MONEY

UAH

price_usd

MONEY

USD

В Inspector отдельного поля должны появиться дополнительные свойства.

Для текстового поля:

- **Language:** uk, ru, en и т. д.
- **Fallback:** запретить / использовать другой язык.
- **Source:** Catalog title, description, content block.
- **Constraints:** максимальная длина именно этого поля.

Для денежного поля:

- **Currency:** UAH, USD, EUR.
- **Price source:** итоговая цена PricingPolicy.
- **Markup:** ссылка на применяемую PricePolicy, с возможностью посмотреть расчёт.
- **Rounding:** вверх до 0.1, 1, 10 и т. д.
- **Override:** ручная окончательная цена.

А на уровне Feed появится вкладка **«Ценообразование»**, в которой можно выбрать или создать PricePolicy и задать базовую наценку сразу для всех товаров.

Не следует копировать настройку «+20%» в каждое поле `price_uah`, `price_usd`, `price_eur`. Это создаст дублирование и риск несовпадающих правил.

## **9. Важное различие: универсальный XML и профиль конкретной площадки**

Универсальный Feed может формировать такую структуру:

```
<product>
    <title_uk>Хлорофіл NOW Foods</title_uk>
    <title_ru>Хлорофилл NOW Foods</title_ru>
    <price_uah>1200.00</price_uah>
    <price_usd>30.00</price_usd>
</product>
```

Но это не означает, что любой маркетплейс примет такую структуру.

Для стандартного Prom YML цена обычно представляется через `price` и `currencyId`, а двуязычные названия и описания имеют отдельные теги. В другом поддерживаемом Prom формате — XML Price.ua — предусмотрены необязательные поля `priceusd` и `priceuah`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://support.prom.ua\&sz=32)

Довідка для продавців+1



Следовательно, **схема Feed и схема внешнего формата должны оставаться разными понятиями**.

```
Feed Schema
    ↓
Resolved Publication
    ↓
FormatProfile
    ├── Generic CSV
    ├── Generic XML
    ├── Prom YML
    └── Rozetka XML
```

`FormatProfile` определяет, какие поля экспортируются, как они называются, какие валюты допустимы и какие поля обязательны.

Для Generic CSV/XML пользователь свободно задаёт структуру. Для Prom/Rozetka будут действовать ограничения конкретного формата.

## **10. Что изменить в плане реализации**

Предлагаю актуализировать ранее согласованные срезы следующим образом.

| Срез                          | Дополнения                                                                                      |
| ----------------------------- | ----------------------------------------------------------------------------------------------- |
| **1. Domain Foundation**      | `FieldDefinition.locale`, `FieldDefinition.currency`, `SourceReference`, типизированные MoneyVO |
| **2. Persistence**            | Удалить обязательные `feed.currency_code`, `feed.locale_code`; добавить `pricing_policy_id`     |
| **3. Schema Builder**         | Выбор языка для текстовых полей и валюты для Money                                              |
| **4. Publication Resolution** | Локализованные источники и получение `PriceQuote`                                               |
| **5. Pricing Engine**         | `PricePolicy`, MarkupRule, CurrencyConversion, версии политик                                   |
| **6. Export Engine**          | Многоязычные и мультивалютные поля в одной выгрузке                                             |
| **7. Public Distribution**    | Без изменений основной архитектуры                                                              |

### **Что должно войти в первый MVP**

Я бы уже сейчас реализовал:

- Независимые языки и валюты полей.
- Несколько текстовых и денежных полей в одном Feed.
- Наценку `PERCENT` на уровне всего Feed.
- Отдельную PricePolicy для каждого прайс-листа.
- Выбор базовой цены Catalog.
- Конвертацию через существующий или минимальный Currency Provider.
- Округление на уровне отдельного денежного поля.
- Ручные overrides каждой языковой версии и каждой валютной цены.
- Фиксацию версий ценовой политики и курсов при генерации.

А наценки на уровне категорий, SKU, поставщиков, минимальную маржу, комиссии торговых площадок и сложные комбинации правил можно добавить следующими срезами.

При этом стоит сразу предусмотреть, что отсутствие курса или исходной цены делает соответствующее поле `INVALID`, а не приводит к использованию устаревшего или условного значения.

## **11. Итоговая модель**

В результате для одного товара будут существовать разные PriceQuote и локализованные поля, но не отдельные копии Catalog Item.

```
CatalogItem
    │
    ├── Localized Content
    │     ├── title[uk]
    │     ├── title[ru]
    │     ├── description[uk]
    │     └── description[ru]
    │
    └── Base Price
          │
          ├── Feed A → PricingPolicy A (+20%)
          │                ├── UAH
          │                └── USD
          │
          └── Feed B → PricingPolicy B (+30%)
                           ├── UAH
                           └── EUR
```

А в `FeedPublication` сохраняются только связь с товаром и индивидуальные overrides. Например, если переопределить русский заголовок и цену в USD, украинский заголовок и цена в UAH продолжат вычисляться автоматически.

**Моя итоговая рекомендация:** сделать `FeedSchema` полностью независимой от языка и валюты Feed, а `PricePolicy` — самостоятельным версионируемым объектом Pricing с привязкой к конкретному прайс-листу.

Это даст три важных свойства: один Feed сможет экспортировать несколько языков и валют; разные Feed получат собственное ценообразование; а Channels сможет использовать те же ценовые правила, что и XML/CSV-выгрузки, исключая конфликт между импортом фида и API-синхронизацией.