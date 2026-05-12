Я бы разложил `communication` на 5 доменных aggregate, а `queue` и `webhook` оставить не aggregate, а application/infrastructure процессами вокруг доставки.

**1. `provider_connector`**
Root: `ProviderConnector`

Внутри:
- `ProviderConnector`
- `ProviderMessageType`

Смысл: это описание провайдера из YAML: тип коннектора, provider code, message types, channel, field schema, ui schema, status.

Почему один aggregate: `ProviderMessageType` не имеет самостоятельного смысла без `ProviderConnector`; он является частью контракта провайдера.

Пример структуры:

```text
domain/provider_connector/
├── entity.py
├── enum.py
├── error.py
├── repository.py
└── value_object/
```

**2. `provider_connection`**
Root: `ProviderConnection`

Смысл: tenant-scoped подключение к конкретному provider connector: connection code/name, config, secrets, status.

Почему отдельно от `provider_connector`: connector это глобальная спецификация провайдера, connection это tenant-конфигурация и секреты. У них разные lifecycle и разные правила безопасности.

```text
domain/provider_connection/
├── entity.py
├── enum.py
├── error.py
├── repository.py
├── service.py
└── value_object/
```

**3. `message_template`**
Root: `MessageTemplate`

Внутри:
- `MessageTemplate`
- `TemplateVersion`

Смысл: шаблон сообщения и его версии.

Почему один aggregate: версия не должна активироваться отдельно от шаблона; правило “только одна ACTIVE version” принадлежит aggregate `MessageTemplate`.

```text
domain/message_template/
├── entity.py
├── enum.py
├── error.py
├── repository.py
├── service.py
└── value_object/
```

**4. `outbound_message`**
Root: `OutboundMessage`

Внутри:
- `CommunicationRequest`
- `OutboundMessage`

Смысл: принятый запрос на отправку и конкретное исходящее сообщение провайдеру.

Тут есть развилка. Если один `CommunicationRequest` всегда порождает ровно один `OutboundMessage`, их можно держать в одном aggregate `outbound_message`. Если позже один request сможет порождать несколько сообщений по разным каналам/провайдерам, тогда `CommunicationRequest` лучше выделить в отдельный aggregate.

Для текущего модуля я бы начал так:

```text
domain/outbound_message/
├── entity.py
├── enum.py
├── error.py
├── repository.py
├── service.py
└── value_object/
```

**5. `delivery`**
Root: скорее `OutboundMessage`, но как поддомен можно выделить `delivery`

Внутри:
- `DeliveryAttempt`
- `DeliveryEvent`

DDD-вариант зависит от транзакционных правил:

Если attempts/events всегда меняются только через `OutboundMessage`, то они должны быть частью aggregate `outbound_message`, а папка `delivery` не нужна в domain.

Если delivery history живет как append-only журнал и webhook может создать event даже когда outbound message не найден, тогда `DeliveryEvent` лучше сделать отдельным aggregate в `domain/delivery`.

С учетом текущей модели, где `DeliveryEvent.outbound_message_id` nullable, я бы выделил `delivery` отдельно:

```text
domain/delivery/
├── entity.py
├── enum.py
├── error.py
├── repository.py
└── value_object/
```

**Что не делать aggregate**
`queue` не aggregate. Это application/infrastructure процесс над `OutboundMessage`:

```text
application/queue/
infrastructure/rabbitmq.py
```

`webhook` тоже не aggregate. Это входной сценарий, который:
- валидирует provider payload;
- находит provider connection / outbound message;
- создает delivery event;
- обновляет outbound message status.

То есть `webhook` может остаться в `application/webhook`, но domain-сущности для него должны лежать в `delivery` и `outbound_message`.

**Рекомендуемая итоговая нарезка**
```text
communication/
├── domain/
│   ├── provider_connector/
│   ├── provider_connection/
│   ├── message_template/
│   ├── outbound_message/
│   └── delivery/
├── application/
│   ├── provider_connector/
│   ├── provider_connection/
│   ├── message_template/
│   ├── outbound_message/
│   ├── delivery/
│   ├── queue/
│   └── webhook/
├── infrastructure/
│   ├── provider_connector/
│   ├── provider_connection/
│   ├── message_template/
│   ├── outbound_message/
│   ├── delivery/
│   ├── provider_sender/
│   └── queue/
└── presentation/
    ├── depends/
    └── http/
```

Ключевая правка относительно текущего состояния: не держать все domain models в `domain/models.py` и один общий `CommunicationRepository`. Лучше разнести модели, errors, enums, repositories и services по aggregate, как это сделано в `inventory/product` и `inventory/category`.