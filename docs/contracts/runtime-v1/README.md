# Runtime v1: схемы и примеры

JSON Schema draft 2020-12 генерируется из актуальных Pydantic-моделей Runtime. UUID, имена и адреса в `examples/` синтетические; значение `EXAMPLE_ONLY_NOT_A_REAL_SECRET` — явная заглушка, не credential. Файлы не читают конфигурацию окружения, ключи или данные рабочей установки.

| Направление | HTTP | Схема запроса / успешного ответа |
| --- | --- | --- |
| Core → Runtime | `POST /internal/v1/tenant-provisioning/` → `202` | `provisioning-command.schema.json` / `attempt-response.schema.json` |
| Core → Runtime | `GET /internal/v1/tenant-provisioning/{attempt_id}/` → `200` | — / `attempt-response.schema.json` |
| Core → Runtime | `GET /internal/v1/status/` → `200` | — / `status-response.schema.json` |
| Runtime → Core | `PUT /internal/v1/tenants/{tenant_id}/access/{user_id}/` → `200` | `access-put-request.schema.json` / `access-put-response.schema.json` |

В provisioning-команде **нет** поля `protocol_version`; версия `1` находится в status. `Idempotency-Key` равен канонической строке `attempt_id`. Ответы Runtime не имеют обёртки `data`; успешный ответ Core имеет `{"status":200,"data":...}`. При `applied=false` версия может отсутствовать. При `applied=true` Runtime дополнительно сверяет подтверждённую версию с отправленной; если версия есть при `applied=false`, она не может быть меньше отправленной.

Помимо структурной схемы Runtime проверяет привязку hostname к разрешённой зоне, точные issuer и callback, неизменяемость команды и сохранённое состояние ресурсов. Эти проверки зависят от конфигурации и БД. `succeeded` допустим только с `present` и непустым `runtime_tenant_id`. `failed + absent` означает подтверждённое отсутствие ресурсов; `404` GET попытки такого подтверждения не даёт. Неизвестные поля, неверные JSON/UUID/Host/issuer/callback дают `422`, конфликт сохранённой команды — `409`, отсутствие management identity — `403`. Служебные запросы требуют отдельного management Host и проверенного mTLS peer.

Обновление и проверка артефактов из корня репозитория:

```sh
python -m scripts.export_runtime_contracts
python -m scripts.export_runtime_contracts --check
python -m unittest test.test_runtime_contract_artifacts
```

Тесты проверяют отсутствие расхождений, валидируют каждый пример текущими моделями и пропускают provisioning/status/attempt примеры через настоящий HTTP router с изолированной подстановкой persistence. PostgreSQL/RabbitMQ/Redis сценарии остаются в `test/test_control_plane_runtime.py`.

## Настоящий Core и mTLS

Повторяемый verifier находится в `test/integration_support/runtime_access_verifier.py`. Он запускает реальный Core в дочернем процессе с временной SQLite БД, создаёт отдельного получателя доступа, пишет Runtime outbox в выделенную тестовую PostgreSQL БД и вызывает production `AccessDelivery` через HTTPS без подмены транспорта. После проверки удаляет только собственные UUID из Runtime и Core и завершает дочерний Core.

Нужны отдельная тестовая PostgreSQL БД, установленное окружение соседнего Core и тестовый nginx/TLS ingress. В каталоге `--tls-dir` должны быть `ca.crt`, `runtime.crt`, `runtime.key`. Nginx обслуживает `core.example.test` и `core-management.example.test`, проксирует оба имени на указанный `--bridge-bind`, а для management включает проверку клиентского сертификата и передаёт `ssl-client-verify`/экранированный PEM `ssl-client-cert`. Тестовый сертификат Runtime автоматически регистрируется только в одноразовом Core. CA и имена должны соответствовать сертификатам; проверки TLS не отключаются.

```sh
export TEST_CP_POSTGRES_URL='postgresql+asyncpg://test_user:test_password@127.0.0.1:55439/provisioning_test'
python -m test.integration_support.runtime_access_verifier \
  --core-repository ../dnk-control-plane \
  --tls-dir /absolute/path/to/disposable-tls-fixture \
  --bridge-bind 0.0.0.0:18090 \
  --connect-address 127.0.0.1
```

`--connect-address` задаёт только тестовое DNS-разрешение двух имён, сохраняя исходные Host/SNI и проверку CA. Для уже работающего disposable bridge можно использовать `--metadata-file` вместо `--core-repository`; private JSON должен содержать его control token, а сертификат Runtime уже должен быть зарегистрирован в этом bridge. Verifier создаёт новый Tenant для каждого запуска, поэтому проверки можно повторять без очистки чужих fixture-данных.

Критерии: доставка отзыва v2, доставка устаревшего grant v1 без восстановления доступа, новая привязка v3 и повтор того же события v3 после имитации потери acknowledgment. В конце Core содержит версию 3 и ровно 3 события, а все 3 Runtime outbox-записи подтверждены. Реальные контрольные токены, client secret, сертификаты и private keys не печатаются и не сохраняются в репозитории.
