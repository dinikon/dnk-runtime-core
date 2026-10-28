# Общее шифрование секретов

Channels и Control Plane используют один `Cipher` из Shared и единственную
конфигурацию `ENCRYPTION`. Рефакторинг не меняет API бизнес-модулей, SQL-структуру,
формат существующих Fernet-токенов или состояния фоновых процессов.

## Контракты и сборка

- `shared/application/crypto/cipher.py`: порт `Cipher` с операциями над байтами и
  явными `encrypt_text` / `decrypt_text` для UTF-8 строк.
- `shared/infrastructure/crypto/fernet_cipher.py`: единственная реализация Fernet.
- `shared/presentation/crypto/depends.py`: общая сборка `get_cipher` / `CipherDep`
  из конфигурации проекта. HTTP, worker и CLI используют эту сборку.
- `config/infrastructure/encryption_config.py`: загрузка и проверка ключа.

Application зависит от порта; криптобиблиотека остаётся в Infrastructure.
Control Plane получает Cipher явно через внешнюю сборку. Channels переводит
`CipherNotConfigured` в прежний `channels_not_configured` / HTTP 503, а
`CiphertextUnreadable` — в `credentials_unreadable`. Worker по-прежнему откладывает
проверку при отсутствии ключа и сохраняет ошибку при нечитаемых credentials.

Бинарные токены Channels остаются `bytes`; токены Control Plane остаются ASCII
строками. Общий Cipher совместим с прежними токенами при сохранении прежнего ключа.

## Конфигурация

Выбрать один источник:

```dotenv
ENCRYPTION__KEY=<existing-persistent-Fernet-key>
```

или:

```dotenv
ENCRYPTION__KEY_PATH=/var/run/dnk/encryption.key
```

Файл должен содержать один постоянный Fernet-ключ; перевод строки в конце допустим.
API и все worker должны использовать один ключ. В коде он доступен как
`dnk_config.ENCRYPTION.resolved_key`; ключ из файла не копируется в настройки модулей.
Значения ключа скрыты в repr и стандартных сообщениях об ошибках конфигурации.

Пустая конфигурация не генерирует новый ключ. Channels остаётся доступен для чтения,
а операции, требующие шифрования, возвращают прежний операционный отказ.
Включённый Control Plane по-прежнему требует настроенный ключ при старте.

Для совместимости принимаются прежние переменные:

- `CHANNELS__CREDENTIALS_ENCRYPTION_KEY`;
- `CONTROL_PLANE__SECRET_ENCRYPTION_KEY`;
- `CONTROL_PLANE__ENCRYPTION_KEY_PATH`.

Они сводятся к `ENCRYPTION`, отдельные конфиги шифрования модулей удалены.
Приоритет env над dotenv сохраняется для одного и того же имени. Если разные
источники указывают разные ключи, старт отклоняется без вывода значений.
Не выбирать один из разных прежних ключей наугад: данные, созданные другим ключом,
потребуют отдельно согласованной перешифровки с доступом к обоим ключам. Этот
рефакторинг не изменяет сохранённые данные автоматически и не выполняет ротацию.

## Развёртывание и переход

1. Сохранить используемый постоянный ключ вместе с резервной копией БД.
2. Перенести его в `ENCRYPTION__KEY` либо оставить прежний файл и указать
   `ENCRYPTION__KEY_PATH`. Значение ключа не менять.
3. Передать один источник API, cron и lifecycle worker; после перехода убрать
   прежние имена переменных из окружения.

Compose использует общие имена переменных; Control Plane overlay передаёт его
существующий `encryption.key` и cron/event worker, монтируя им только этот файл.
Helm поддерживает `application.encryption.key` (`value` или `existingSecret`).
При включённом Control Plane и отсутствии явной общей настройки переиспользуется
прежний `controlPlane.credentialsSecret` / `encryption.key`. Ключ передаётся всем
Python workload, а TLS-credentials остаются у потребителей Control Plane.
Frontend и миграционный Job общий ключ не получают.

## Проверки

`test/test_shared_cipher.py` проверяет оба прежних формата, ошибочный/отсутствующий
ключ, env/dotenv, файлы, старые имена, конфликт источников и единую сборку Cipher.
Сквозные наборы Channels и Control Plane проверяются на отдельных disposable
PostgreSQL БД, поскольку их тестовые очереди содержат разные типы заданий.
