import unittest

from fastapi.testclient import TestClient

from src.dnk_app import DnkApp
from src.modules.router import router as api_router


class MockWorkplacesEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = DnkApp()
        self.app.include_router(api_router)
        self.client_context = TestClient(self.app)
        self.client = self.client_context.__enter__()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)

    def test_returns_expected_workplaces_payload(self) -> None:
        response = self.client.get("/api/mock/workplaces")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "meta": {
                    "contractVersion": "1.0",
                    "generatedAt": "2026-03-05T20:00:00Z",
                },
                "data": {
                    "user": {
                        "id": "u_001",
                        "name": "Denis",
                        "email": "denis@example.com",
                    },
                    "workplaces": [
                        {
                            "id": "crm",
                            "emoji": "🧩",
                            "title": "CRM",
                            "description": "Лиды, сделки, клиенты",
                            "defaultEntityKey": "deal",
                        },
                        {
                            "id": "support",
                            "emoji": "🎧",
                            "title": "Support",
                            "description": "Тикеты и обращения",
                            "defaultEntityKey": "ticket",
                        },
                    ],
                    "activeWorkplaceId": "crm",
                },
            },
        )

    def test_returns_expected_crm_workplace_payload(self) -> None:
        response = self.client.get("/api/mock/workplaces/crm")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "meta": {
                    "workplace": {
                        "id": "crm",
                        "emoji": "🧩",
                        "title": "CRM",
                    }
                },
                "data": {
                    "entityGroups": [
                        {
                            "type": "flat",
                            "items": [
                                {
                                    "entityKey": "lead",
                                    "title": "Lead",
                                    "emoji": "📥",
                                },
                                {
                                    "entityKey": "deal",
                                    "title": "Deal",
                                    "emoji": "💼",
                                },
                            ],
                        },
                        {
                            "type": "dropdown",
                            "title": "Клиенты",
                            "emoji": "👥",
                            "items": [
                                {
                                    "entityKey": "contact",
                                    "title": "Contact",
                                    "emoji": "👤",
                                },
                                {
                                    "entityKey": "company",
                                    "title": "Company",
                                    "emoji": "🏢",
                                },
                            ],
                        },
                    ]
                },
            },
        )

    def test_returns_expected_deal_entity_payload(self) -> None:
        response = self.client.get("/api/mock/workplaces/crm/entities/deal")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "meta": {
                    "entityKey": "deal",
                    "workplaceId": "crm",
                },
                "data": {
                    "entity": {
                        "key": "deal",
                        "title": "Deal",
                        "emoji": "💼",
                        "features": {
                            "customFields": True,
                            "pipelines": True,
                            "timeline": True,
                            "robots": True,
                        },
                    },
                    "views": [
                        {
                            "id": "table_default",
                            "type": "table",
                            "title": "Таблица",
                            "isDefault": True,
                        },
                        {
                            "id": "kanban_by_stage",
                            "type": "kanban",
                            "title": "Канбан (по стадиям)",
                        },
                        {
                            "id": "calendar_by_close",
                            "type": "calendar",
                            "title": "Календарь (по закрытию)",
                        },
                    ],
                },
            },
        )

    def test_returns_mock_payload_for_company_entity(self) -> None:
        response = self.client.get("/api/mock/workplaces/crm/entities/company")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["entityKey"], "company")
        self.assertEqual(payload["meta"]["workplaceId"], "crm")
        self.assertEqual(payload["data"]["entity"]["key"], "company")
        self.assertEqual(payload["data"]["entity"]["title"], "Company")
        self.assertEqual(payload["data"]["entity"]["emoji"], "🏢")
        self.assertEqual(
            payload["data"]["entity"]["features"],
            {
                "customFields": True,
                "pipelines": False,
                "timeline": True,
                "robots": False,
            },
        )
        self.assertEqual(len(payload["data"]["views"]), 2)

    def test_returns_404_for_unknown_crm_entity(self) -> None:
        response = self.client.get("/api/mock/workplaces/crm/entities/unknown")

        self.assertEqual(response.status_code, 404)
