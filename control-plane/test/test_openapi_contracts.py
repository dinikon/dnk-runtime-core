import copy
import re
import unittest
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

import yaml
from fastapi.openapi.models import OpenAPI

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1]
AGENT_CONTRACT = CONTROL_PLANE_ROOT / "contracts" / "agent-control" / "openapi.yaml"
RUNTIME_CONTRACT = (
    CONTROL_PLANE_ROOT / "contracts" / "runtime-management" / "openapi.yaml"
)
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
MUTATION_METHODS = {"post", "put", "patch", "delete"}


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _resolve(document: dict, value: dict) -> dict:
    if "$ref" not in value:
        return value
    reference = value["$ref"]
    if not reference.startswith("#/"):
        raise AssertionError(f"Only local references are allowed: {reference}")
    current: object = document
    for part in reference[2:].split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or key not in current:
            raise AssertionError(f"Unresolved reference: {reference}")
        current = current[key]
    if not isinstance(current, dict):
        raise AssertionError(f"Reference does not resolve to an object: {reference}")
    return current


def _walk(value: object):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _normalized_for_fastapi(document: dict) -> dict:
    normalized = copy.deepcopy(document)
    schemes = normalized.get("components", {}).get("securitySchemes", {})
    for name, scheme in list(schemes.items()):
        if scheme.get("type") == "mutualTLS":
            schemes[name] = {
                "type": "apiKey",
                "in": "header",
                "name": "X-Validated-Client-Certificate",
                "description": scheme.get("description"),
            }
    return normalized


def _assert_example(instance: object, schema: dict, document: dict, path: str) -> None:
    schema = _resolve(document, schema)

    if "allOf" in schema:
        for index, child in enumerate(schema["allOf"]):
            _assert_example(instance, child, document, f"{path}.allOf[{index}]")
    if "oneOf" in schema:
        successes = 0
        for child in schema["oneOf"]:
            try:
                _assert_example(instance, child, document, path)
            except AssertionError:
                continue
            successes += 1
        if successes != 1:
            raise AssertionError(f"{path}: expected one oneOf match, got {successes}")

    if "const" in schema and instance != schema["const"]:
        raise AssertionError(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        raise AssertionError(f"{path}: value {instance!r} is not in enum")

    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(instance, dict):
            raise AssertionError(f"{path}: expected object")
        required = set(schema.get("required", []))
        missing = required - set(instance)
        if missing:
            raise AssertionError(f"{path}: missing properties {sorted(missing)}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extras = set(instance) - set(properties)
            if extras:
                raise AssertionError(f"{path}: unexpected properties {sorted(extras)}")
        for key, child in properties.items():
            if key in instance:
                _assert_example(instance[key], child, document, f"{path}.{key}")
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            for key in set(instance) - set(properties):
                _assert_example(instance[key], additional, document, f"{path}.{key}")
    elif expected_type == "array":
        if not isinstance(instance, list):
            raise AssertionError(f"{path}: expected array")
        if len(instance) < schema.get("minItems", 0):
            raise AssertionError(f"{path}: too few items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise AssertionError(f"{path}: too many items")
        for index, item in enumerate(instance):
            _assert_example(item, schema["items"], document, f"{path}[{index}]")
    elif expected_type == "string":
        if not isinstance(instance, str):
            raise AssertionError(f"{path}: expected string")
        if len(instance) < schema.get("minLength", 0):
            raise AssertionError(f"{path}: string is too short")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            raise AssertionError(f"{path}: string is too long")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], instance):
            raise AssertionError(f"{path}: string does not match pattern")
        format_name = schema.get("format")
        if format_name == "uuid":
            UUID(instance)
        elif format_name == "date-time":
            datetime.fromisoformat(instance.replace("Z", "+00:00"))
        elif format_name == "email" and "@" not in instance:
            raise AssertionError(f"{path}: invalid email")
        elif format_name == "uri" and not urlparse(instance).scheme:
            raise AssertionError(f"{path}: invalid URI")
    elif expected_type == "integer":
        if not isinstance(instance, int) or isinstance(instance, bool):
            raise AssertionError(f"{path}: expected integer")
        if "minimum" in schema and instance < schema["minimum"]:
            raise AssertionError(f"{path}: value is below minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            raise AssertionError(f"{path}: value is above maximum")
    elif expected_type == "boolean" and not isinstance(instance, bool):
        raise AssertionError(f"{path}: expected boolean")


class OpenApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.agent = _load(AGENT_CONTRACT)
        cls.runtime = _load(RUNTIME_CONTRACT)

    def test_contracts_validate_as_openapi_31(self) -> None:
        for name, document in (("agent", self.agent), ("runtime", self.runtime)):
            with self.subTest(contract=name):
                self.assertEqual(document["openapi"], "3.1.0")
                OpenAPI.model_validate(_normalized_for_fastapi(document))

    def test_all_local_references_resolve(self) -> None:
        for name, document in (("agent", self.agent), ("runtime", self.runtime)):
            for value in _walk(document):
                if "$ref" in value:
                    with self.subTest(contract=name, reference=value["$ref"]):
                        _resolve(document, value)

    def test_all_mutations_require_idempotency_key(self) -> None:
        for name, document in (("agent", self.agent), ("runtime", self.runtime)):
            for route, path_item in document["paths"].items():
                path_parameters = path_item.get("parameters", [])
                for method in MUTATION_METHODS & set(path_item):
                    operation = path_item[method]
                    parameters = path_parameters + operation.get("parameters", [])
                    resolved = [
                        _resolve(document, parameter) for parameter in parameters
                    ]
                    keys = [
                        parameter
                        for parameter in resolved
                        if parameter.get("in") == "header"
                        and parameter.get("name") == "Idempotency-Key"
                    ]
                    with self.subTest(contract=name, route=route, method=method):
                        self.assertEqual(len(keys), 1)
                        self.assertTrue(keys[0]["required"])

    def test_bootstrap_is_only_agent_operation_without_mtls(self) -> None:
        for route, path_item in self.agent["paths"].items():
            for method in HTTP_METHODS & set(path_item):
                security = path_item[method].get(
                    "security", self.agent.get("security", [])
                )
                names = {name for requirement in security for name in requirement}
                with self.subTest(route=route, method=method):
                    if route == "/agent/v1/bootstrap":
                        self.assertEqual(names, {"BootstrapToken"})
                    else:
                        self.assertEqual(names, {"AgentMtls"})
        self.assertEqual(
            self.agent["components"]["securitySchemes"]["AgentMtls"]["type"],
            "mutualTLS",
        )

    def test_problem_responses_have_machine_readable_code(self) -> None:
        for name, document in (("agent", self.agent), ("runtime", self.runtime)):
            problem = document["components"]["schemas"]["ProblemDetails"]
            self.assertIn("code", problem["required"])
            self.assertIn("retryable", problem["required"])
            for route, path_item in document["paths"].items():
                for method in HTTP_METHODS & set(path_item):
                    for status, response in path_item[method]["responses"].items():
                        if not str(status).startswith(("4", "5")):
                            continue
                        resolved = _resolve(document, response)
                        content = resolved.get("content", {})
                        with self.subTest(
                            contract=name, route=route, method=method, status=status
                        ):
                            self.assertIn("application/problem+json", content)
                            schema = content["application/problem+json"]["schema"]
                            self.assertIs(_resolve(document, schema), problem)

    def test_runtime_contract_declares_required_signature_failures(self) -> None:
        operation = self.runtime["paths"][
            "/management/v1/commands/{command_id}/execute"
        ]["post"]
        codes = set(operation["x-error-codes"])
        self.assertTrue(
            {
                "COMMAND_SIGNATURE_EXPIRED",
                "COMMAND_SIGNATURE_KEY_UNKNOWN",
                "INSTALLATION_MISMATCH",
                "IDEMPOTENCY_CONFLICT",
            }.issubset(codes)
        )

    def test_media_type_examples_match_their_schemas(self) -> None:
        for name, document in (("agent", self.agent), ("runtime", self.runtime)):
            example_count = 0
            for route, path_item in document["paths"].items():
                for method in HTTP_METHODS & set(path_item):
                    operation = path_item[method]
                    request_body = operation.get("requestBody", {})
                    if "$ref" in request_body:
                        request_body = _resolve(document, request_body)
                    for media in request_body.get("content", {}).values():
                        if "example" in media:
                            example_count += 1
                            _assert_example(
                                media["example"],
                                media["schema"],
                                document,
                                f"{route}.request",
                            )
                    for status, response in operation["responses"].items():
                        response = _resolve(document, response)
                        for media in response.get("content", {}).values():
                            if "example" in media:
                                example_count += 1
                                _assert_example(
                                    media["example"],
                                    media["schema"],
                                    document,
                                    f"{route}.responses.{status}",
                                )
            self.assertGreater(example_count, 0, name)

    def test_decoded_jws_example_matches_header_and_claim_schemas(self) -> None:
        operation = self.runtime["paths"][
            "/management/v1/commands/{command_id}/execute"
        ]["post"]
        example = operation["x-jws-example"]
        _assert_example(
            example["protected"],
            {"$ref": operation["x-jws-protected-schema"]},
            self.runtime,
            "jws.protected",
        )
        _assert_example(
            example["claims"],
            {"$ref": operation["x-jws-payload-schema"]},
            self.runtime,
            "jws.claims",
        )


if __name__ == "__main__":
    unittest.main()
