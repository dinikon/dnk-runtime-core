from django.test import SimpleTestCase
from django.urls import reverse


class HomePageTests(SimpleTestCase):
    def test_home_page_renders_beta_workflow_hero(self) -> None:
        response = self.client.get(reverse("marketing:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "marketing/home.html")
        self.assertContains(response, "Платформа в Beta")
        self.assertContains(
            response,
            "Автоматизируйте процессы с помощью визуальных Workflow",
        )
        self.assertContains(response, "Обновление CRM")

    def test_home_page_contains_server_rendered_seo_metadata(self) -> None:
        response = self.client.get(reverse("marketing:home"))

        self.assertContains(
            response,
            "DNK — визуальная автоматизация Workflow",
        )
        self.assertContains(response, 'rel="canonical" href="https://dniko.net/"')
        self.assertContains(response, 'property="og:type" content="website"')
