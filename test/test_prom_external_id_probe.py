"""Проверяет доказательство записи external_id и обход API без реальных запросов."""

import json
import contextlib
import io
import logging
import unittest
from typing import Any

import httpx

from scripts.prom_external_id_probe import (
    API_BASE,
    ProbeError,
    SecretFormatter,
    arguments,
    api_diagnostics,
    list_products,
    probe_product,
)


class PromExternalIdProbeTests(unittest.TestCase):
    """Отличает успешный ответ редактирования от фактически сохранённого ключа."""

    def run_probe(self, mode: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Моделирует сервер, который записывает, игнорирует или отклоняет поле."""
        product = {
            "id": 42,
            "external_id": None,
            "price": 10,
            "status": "not_on_display",
        }
        writes: list[dict[str, Any]] = []

        def respond(request: httpx.Request) -> httpx.Response:
            """Возвращает независимые результаты редактирования и повторного чтения."""
            path = request.url.path
            if request.method == "POST":
                payload = json.loads(request.content)
                writes.append(payload[0])
                self.assertEqual(path, "/api/v1/products/edit")
                self.assertEqual(payload, [{"id": 42, "external_id": "probe-42"}])
                if mode in ("written", "other_changes", "timeout_after_write"):
                    product["external_id"] = "probe-42"
                if mode == "other_changes":
                    product["price"] = 99
                if mode.startswith("timeout"):
                    raise httpx.ReadTimeout("timeout", request=request)
                if mode == "rejected":
                    return httpx.Response(400, json={"errors": {"42": "unknown_field"}})
                if mode == "unknown_field":
                    return httpx.Response(
                        200,
                        json={
                            "processed_ids": [],
                            "errors": {"42": {"external_id": ["Unknown field."]}},
                        },
                    )
                return httpx.Response(200, json={"processed_ids": [42], "errors": {}})
            if "/by_external_id/" in path:
                if mode == "collision":
                    return httpx.Response(
                        200, json={"product": {"id": 99, "external_id": "probe-42"}}
                    )
                if product["external_id"] == "probe-42":
                    return httpx.Response(200, json={"product": product})
                return httpx.Response(404, json={})
            return httpx.Response(200, json={"product": product})

        with httpx.Client(
            base_url=API_BASE, transport=httpx.MockTransport(respond)
        ) as client:
            result = probe_product(
                client, 42, "probe", verify_attempts=2, verify_delay=0
            )
        return result, writes

    def test_processed_id_without_persistence_is_not_success(self) -> None:
        """HTTP 200 и processed_ids при проигнорированном поле не доказывают запись."""
        result, writes = self.run_probe("ignored")
        self.assertEqual(len(writes), 1)
        self.assertTrue(result["processed_id_returned"])
        self.assertEqual(result["outcome"], "not_persisted")
        self.assertFalse(result["assignment_verified"])
        self.assertIsNone(result["external_id_after"])
        self.assertTrue(result["other_fields_unchanged"])

    def test_assignment_requires_native_and_external_lookup_agreement(self) -> None:
        """Успех требует нового ключа у исходного native ID и обратного поиска к нему."""
        result, writes = self.run_probe("written")
        self.assertEqual(result["outcome"], "verified")
        self.assertTrue(result["assignment_verified"])
        self.assertEqual(result["lookup_native_id"], 42)
        self.assertEqual(len(writes), 1)

    def test_http_rejection_is_read_back_and_not_retried(self) -> None:
        """Ошибка API записывается отдельно от неизменного состояния товара."""
        result, writes = self.run_probe("rejected")
        self.assertEqual(result["outcome"], "api_rejected")
        self.assertTrue(result["api_errors_present"])
        self.assertEqual(len(writes), 1)
        self.assertTrue(result["other_fields_unchanged"])

    def test_unexpected_other_changes_do_not_pass(self) -> None:
        """Назначенный ключ не скрывает нежелательное изменение цены."""
        result, _ = self.run_probe("other_changes")
        self.assertTrue(result["assignment_verified"])
        self.assertEqual(result["outcome"], "unexpected_other_changes")
        self.assertEqual(result["changed_other_fields"], ["price"])

    def test_http_200_with_unknown_field_is_an_api_rejection(self) -> None:
        """Фактический ответ Prom с HTTP 200 и Unknown field не считается успешной записью."""
        result, writes = self.run_probe("unknown_field")
        self.assertEqual(result["http_status"], 200)
        self.assertEqual(result["outcome"], "api_rejected")
        self.assertFalse(result["assignment_verified"])
        self.assertFalse(result["processed_id_returned"])
        self.assertEqual(
            result["api_diagnostics"],
            [{"path": "errors.42.external_id.0", "detail": "Unknown field."}],
        )
        self.assertEqual(len(writes), 1)

    def test_occupied_key_is_never_written(self) -> None:
        """Существующий внешний ключ другой карточки не переназначается."""
        result, writes = self.run_probe("collision")
        self.assertEqual(result["outcome"], "skipped_key_occupied")
        self.assertEqual(writes, [])

    def test_timeout_does_not_repeat_post_and_can_be_resolved_by_reading(self) -> None:
        """Потерянный ответ после записи разрешается чтением, а не повтором POST."""
        result, writes = self.run_probe("timeout_after_write")
        self.assertEqual(result["outcome"], "verified")
        self.assertIsNone(result["http_status"])
        self.assertEqual(len(writes), 1)

    def test_unresolved_timeout_remains_unknown(self) -> None:
        """Сетевой сбой без подтверждённого ключа не превращается в успех или отказ API."""
        result, writes = self.run_probe("timeout_before_write")
        self.assertEqual(result["outcome"], "delivery_unknown_not_verified")
        self.assertEqual(len(writes), 1)

    def test_existing_nonempty_key_is_preserved(self) -> None:
        """Строковый ключ '0' существует и не считается пустым."""

        def respond(request: httpx.Request) -> httpx.Response:
            """Разрешает только исходное чтение; любой POST ломает проверку."""
            self.assertEqual(request.method, "GET")
            return httpx.Response(200, json={"product": {"id": 42, "external_id": "0"}})

        with httpx.Client(
            base_url=API_BASE, transport=httpx.MockTransport(respond)
        ) as client:
            self.assertEqual(
                probe_product(client, 42, "probe")["outcome"],
                "skipped_already_assigned",
            )

    def test_list_covers_short_pages_and_all_groups(self) -> None:
        """Короткая страница не завершает обход; корневая и дочерние группы дедуплицируются."""

        def respond(request: httpx.Request) -> httpx.Response:
            """Моделирует включительный курсор и меньшие, чем limit, страницы."""
            self.assertEqual(request.method, "GET")
            cursor = request.url.params.get("last_id")
            if request.url.path.endswith("groups/list"):
                ids = {None: [20], "19": [10], "9": []}[cursor]
                return httpx.Response(200, json={"groups": [{"id": i} for i in ids]})
            group = request.url.params.get("group_id")
            ids = {(None, None): [8, 7], ("10", None): [9], ("20", None): [8, 6]}.get(
                (group, cursor), []
            )
            return httpx.Response(
                200, json={"products": [{"id": i, "external_id": None} for i in ids]}
            )

        with httpx.Client(
            base_url=API_BASE, transport=httpx.MockTransport(respond)
        ) as client:
            self.assertEqual(
                {p["id"] for p in list_products(client, 100, 10)}, {6, 7, 8, 9}
            )

    def test_missing_response_field_does_not_mean_empty_external_id(self) -> None:
        """Неполная схема ответа не превращает карточки в кандидатов на запись."""

        def respond(request: httpx.Request) -> httpx.Response:
            """Возвращает товар без поля external_id вместо явного null."""
            key = "groups" if request.url.path.endswith("groups/list") else "products"
            return httpx.Response(
                200, json={key: [] if key == "groups" else [{"id": 9}]}
            )

        with httpx.Client(
            base_url=API_BASE, transport=httpx.MockTransport(respond)
        ) as client:
            with self.assertRaisesRegex(
                ProbeError, "external_id_missing_from_response"
            ):
                list_products(client, 100, 10)

    def test_log_formatter_removes_token(self) -> None:
        """API-ключ не попадает даже в сообщение неожиданной ошибки."""
        formatter = SecretFormatter("synthetic-secret")
        record = logging.LogRecord(
            "probe",
            logging.ERROR,
            __file__,
            1,
            "failed %s",
            ("synthetic-secret",),
            None,
        )
        rendered = formatter.format(record)
        self.assertNotIn("synthetic-secret", rendered)
        self.assertIn("[REDACTED]", rendered)

    def test_apply_requires_selected_product(self) -> None:
        """Запись не включается для всего каталога одним --apply без выбранных ID."""
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as failure:
                arguments(["--apply"])
        self.assertEqual(failure.exception.code, 2)

    def test_repeated_cursor_is_incomplete_scan(self) -> None:
        """Сервер, игнорирующий last_id, не приводит к вечному обходу или ложной полноте."""

        def respond(request: httpx.Request) -> httpx.Response:
            """Повторяет одну страницу групп независимо от параметров курсора."""
            return httpx.Response(200, json={"groups": [{"id": 20}]})

        with httpx.Client(
            base_url=API_BASE, transport=httpx.MockTransport(respond)
        ) as client:
            with self.assertRaisesRegex(ProbeError, "pagination_did_not_advance"):
                list_products(client, 100, 10)

    def test_api_error_projection_is_bounded_and_cleans_control_characters(
        self,
    ) -> None:
        """Причина отказа доступна в логе без полного ответа и произвольных длинных строк."""
        body = {
            "errors": {"42": {"code": "invalid", "message": "bad\n" + "x" * 1000}},
            "product": {"description": "private"},
        }
        diagnostics = api_diagnostics(body)
        self.assertEqual(
            diagnostics[0], {"path": "errors.42.code", "detail": "invalid"}
        )
        self.assertLessEqual(len(diagnostics[1]["detail"]), 240)
        self.assertNotIn("\n", diagnostics[1]["detail"])
        self.assertNotIn("private", json.dumps(diagnostics))


if __name__ == "__main__":
    unittest.main()
