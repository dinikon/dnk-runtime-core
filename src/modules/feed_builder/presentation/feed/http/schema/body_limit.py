from fastapi.routing import APIRoute
from starlette.responses import JSONResponse
from starlette.types import Scope, Receive, Send, Message

MAX_SCHEMA_BYTES = 1024 * 1024
MAX_JSON_DEPTH = 160


def excessive_json_depth(body: bytes | bytearray) -> bool:
    """Ограничивает вложенность до JSON/Pydantic, учитывая экранированные строки."""
    depth = 0
    quoted = False
    escaped = False
    for char in body:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):
            depth += 1
            if depth > MAX_JSON_DEPTH:
                return True
        elif char in (93, 125):
            depth -= 1
    return False


class SchemaBodyLimitRoute(APIRoute):
    """Ограничивает поток тела до его декодирования, включая chunked-запросы."""

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Буферизует ограниченный PUT/POST/PATCH и передаёт исходные ASGI-сообщения обработчику."""
        if scope["method"] not in {"PUT", "POST", "PATCH"}:
            await super().handle(scope, receive, send)
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > MAX_SCHEMA_BYTES:
                await JSONResponse(
                    {
                        "detail": {
                            "code": "SCHEMA_TOO_LARGE",
                            "message": "Схема превышает лимит 1 МиБ.",
                        }
                    },
                    status_code=413,
                )(scope, receive, send)
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break
        if excessive_json_depth(body):
            await JSONResponse(
                {
                    "detail": {
                        "code": "SCHEMA_LIMIT_EXCEEDED",
                        "message": "Превышена глубина документа.",
                    }
                },
                status_code=422,
            )(scope, receive, send)
            return
        consumed = False

        async def replay() -> Message:
            """Передаёт ограниченное тело один раз, затем сохраняет исходный receive."""
            nonlocal consumed
            if consumed:
                return await receive()
            consumed = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await super().handle(scope, replay, send)
