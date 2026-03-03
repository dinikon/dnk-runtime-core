# Config Module

## Ответственность

`src/config` хранит все runtime-настройки приложения и агрегирует их через `DnkConfig`.

Ключевой файл:

- [`src/config/app_config.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/config/app_config.py)

## Состав config-групп

### `DatabaseConfig`

Файл:

- [`src/config/infrastructure/__init__.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/config/infrastructure/__init__.py)

Отвечает за:

- SQLAlchemy URI
- pool settings
- engine options

### `RedisConfig`

Файл:

- [`src/config/redis_config.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/config/redis_config.py)

Поля:

```python
REDIS_HOST: str
REDIS_PORT: int
REDIS_USERNAME: str
REDIS_PASSWORD: str
REDIS_USE_SSL: bool
REDIS_DB: int
```

### `IdentityAuthConfig`

Файл:

- [`src/config/auth_config.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/config/auth_config.py)

Поля:

```python
AUTH.otp_code_length: int
AUTH.otp_token_ttl_seconds: int
AUTH.session_ttl_seconds: int
AUTH.session_cookie_name: str
```

### `ControlPlaneConfig`

Файл:

- [`src/config/control_plane.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/config/control_plane.py)

Поля:

```python
CONTROL_PLANE_API_KEY: str
```

### `PackagingInfo`

Файлы:

- [`src/config/packaging/__init__.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/config/packaging/__init__.py)
- [`src/config/packaging/pyproject.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/config/packaging/pyproject.py)

Отвечает за metadata из `pyproject.toml`.

## Источники настроек

`DnkConfig.settings_customise_sources(...)` использует:

1. init settings
2. env settings
3. dotenv settings
4. file secret settings
5. `pyproject.toml`

## Особенности

- включен `env_nested_delimiter="__"`
- auth-настройки читаются как `AUTH__...`
- единый объект конфигурации доступен через:

```python
from src.config import dnk_config
```
