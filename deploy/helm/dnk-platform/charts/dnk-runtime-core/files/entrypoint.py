"""Translate Secret-backed connection URLs for the unchanged runtime image."""

import os
import sys
from urllib.parse import quote, unquote, urlsplit


class ConfigurationError(ValueError):
    """A connection setting is invalid; messages never include its value."""


def connection_url(value, schemes):
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in schemes
            or not parsed.hostname
            or parsed.fragment
            or parsed.query
            or any(char.isspace() for char in parsed.netloc)
        ):
            raise ValueError
        # Validate even when the caller needs the original AMQP URL.
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError
        return parsed
    except ValueError:
        raise ConfigurationError("Invalid connection URL") from None


def configure_environment(env):
    """Mutate only environment, never arguments; URL credentials remain private."""
    redis_url = env.pop("DNK_REDIS_URL", "")
    if redis_url:
        parsed = connection_url(redis_url, {"redis", "rediss"})
        db = parsed.path.removeprefix("/") or "0"
        if not db.isascii() or not db.isdecimal():
            raise ConfigurationError("Redis URL requires an integer database path")
        env.update(
            REDIS_HOST=parsed.hostname,
            REDIS_PORT=str(parsed.port or 6379),
            REDIS_USERNAME=unquote(parsed.username or ""),
            REDIS_PASSWORD=unquote(parsed.password or ""),
            REDIS_USE_SSL=str(parsed.scheme == "rediss").lower(),
            REDIS_DB=db,
        )
    rabbit_url = env.pop("DNK_RABBITMQ_URL", "")
    if rabbit_url:
        connection_url(rabbit_url, {"amqp", "amqps"})
    elif env.get("RABBITMQ__ENABLED", "false").lower() == "true":
        host = env.get("DNK_RABBITMQ_HOST", "")
        if not host or any(char in host for char in "/@?# \t\r\n"):
            raise ConfigurationError("Invalid RabbitMQ host")
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        try:
            port = int(env.get("DNK_RABBITMQ_PORT", "5672"))
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            raise ConfigurationError("Invalid RabbitMQ port") from None
        scheme = (
            "amqps"
            if env.get("DNK_RABBITMQ_USE_SSL", "false").lower() == "true"
            else "amqp"
        )
        username = quote(env.get("DNK_RABBITMQ_USERNAME", ""), safe="")
        password = quote(env.get("DNK_RABBITMQ_PASSWORD", ""), safe="")
        vhost = quote(env.get("DNK_RABBITMQ_VHOST", "/"), safe="")
        rabbit_url = f"{scheme}://{username}:{password}@{host}:{port}/{vhost}"
    if rabbit_url:
        env["RABBITMQ__URL"] = rabbit_url
    for key in list(env):
        if key.startswith("DNK_RABBITMQ_"):
            del env[key]


def main():
    try:
        configure_environment(os.environ)
        if len(sys.argv) < 2:
            raise ConfigurationError("A runtime command is required")
        os.execvp(sys.argv[1], sys.argv[1:])
    except (ConfigurationError, OSError) as error:
        print(f"Runtime startup failed ({type(error).__name__})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
