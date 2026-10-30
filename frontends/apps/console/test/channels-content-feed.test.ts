import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { createServer, type ViteDevServer } from "vite";
import vue from "@vitejs/plugin-vue";
import { createSSRApp, type Component } from "vue";
import { renderToString } from "vue/server-renderer";
import type { FeedImportDto } from "../src/modules/channels/api/content-feed.dto.ts";
import {
  mapFeedImport,
  requestFeedImportPayload,
  attachFeedImportPayload,
  resolveFeedImportPayload,
} from "../src/modules/channels/api/content-feed.mapper.ts";
import {
  feedSubmissionLabel,
  feedReportLabel,
  feedVerificationLabel,
} from "../src/modules/channels/model/content-feed.display.ts";

function fixture(): FeedImportDto {
  return {
    revision: 4,
    phase: "completed",
    operation_id: "operation",
    external_import_id: "77",
    submission: "accepted",
    force_update: false,
    requested_at: "2026-10-30T12:00:00Z",
    submission_started_at: "2026-10-30T12:00:01Z",
    last_checked_at: "2026-10-30T12:00:20Z",
    finished_at: "2026-10-30T12:00:20Z",
    error_code: "feed_import_content_unconfirmed",
    manual_resolution: null,
    report: {
      status: "SUCCESS",
      total: 2,
      updated: 1,
      created: 0,
      imported: null,
      not_changed: null,
      not_in_file: null,
      with_errors_count: 0,
      issues: [],
    },
    verification: [
      {
        publication_id: "publication",
        external_id: "99",
        import_key: "001",
        fields: [
          { field: "title", locale: "ru", status: "confirmed" },
          { field: "gallery", locale: null, status: "unconfirmed" },
        ],
        observed_gallery: ["https://images.prom.ua/501.jpg"],
      },
    ],
    recovery_required: false,
    can_start: true,
    can_resume: false,
    can_attach: false,
    can_resolve: false,
  };
}

test("command payloads contain concurrency tokens and explicit manual decisions", () => {
  const version = {
    channelId: "channel",
    feedId: "feed",
    expectedRevision: 3,
    expectedDeliveryRevision: 4,
  };
  assert.deepEqual(
    requestFeedImportPayload({
      ...version,
      requestId: "request",
      forceUpdate: false,
    }),
    {
      expected_revision: 3,
      expected_delivery_revision: 4,
      request_id: "request",
      force_update: false,
    },
  );
  assert.deepEqual(attachFeedImportPayload({ ...version, externalId: "77" }), {
    expected_revision: 3,
    expected_delivery_revision: 4,
    external_id: "77",
  });
  assert.deepEqual(
    resolveFeedImportPayload({ ...version, confirmNotSubmitted: true }),
    {
      expected_revision: 3,
      expected_delivery_revision: 4,
      confirm_not_submitted: true,
    },
  );
});

test("accepted URL, provider report and applied content remain independent", () => {
  const value = mapFeedImport(fixture());
  assert.equal(value.report?.notChanged, null);
  assert.equal(value.report?.created, 0);
  assert.equal(value.verification[0]?.importKey, "001");
  assert.equal(feedSubmissionLabel(value), "Ссылка принята");
  assert.equal(feedReportLabel(value), "Импорт завершён");
  assert.equal(
    feedVerificationLabel(value),
    "Применение подтверждено не полностью",
  );
  const changed = {
    ...value,
    verification: value.verification.map((v) => ({
      ...v,
      fields: v.fields.map((f) => ({ ...f, status: "obsolete" as const })),
    })),
  };
  assert.equal(feedVerificationLabel(changed), "Представление изменилось");
});

let server: ViteDevServer;
let Panel: Component;
let Form: Component;
before(async () => {
  server = await createServer({
    configFile: false,
    plugins: [vue()],
    optimizeDeps: { noDiscovery: true },
    server: { middlewareMode: true, ws: false, watch: null },
    resolve: {
      alias: { "@": fileURLToPath(new URL("../src", import.meta.url)) },
    },
  });
  Panel = (
    await server.ssrLoadModule(
      "/src/modules/channels/ui/feeds/FeedImportPanel.vue",
    )
  ).default;
  Form = (
    await server.ssrLoadModule(
      "/src/modules/channels/ui/feeds/ContentFeedForm.vue",
    )
  ).default;
});
after(async () => server?.close());

test("panel shows field evidence and unavailable counters without claiming full application", async () => {
  const html = await renderToString(
    createSSRApp(Panel, {
      operation: mapFeedImport(fixture()),
      busy: false,
      ready: true,
      enabled: true,
      verified: true,
      publicationLinks: {
        publication: "/channels/channel/publications/publication",
      },
    }),
  );
  for (const text of [
    "Передача ссылки",
    "Ссылка принята",
    "Импорт Prom",
    "Импорт завершён",
    "Применение контента",
    "Не подтверждено",
    "Нет данных",
    "Публикация 99",
    "001",
  ])
    assert.ok(html.includes(text), text);
  assert.doesNotMatch(
    html,
    /Контент подтверждён|token=|delivery_request|encrypted/,
  );
});

test("unknown acceptance exposes manual reconciliation and disables a new import", async () => {
  const operation = mapFeedImport({
    ...fixture(),
    phase: "unknown",
    submission: "unknown",
    report: null,
    verification: [],
    external_import_id: null,
    can_start: false,
    can_attach: true,
    can_resolve: true,
    error_code: "feed_import_acceptance_unknown",
  });
  const html = await renderToString(
    createSSRApp(Panel, {
      operation,
      busy: false,
      ready: true,
      enabled: true,
      verified: true,
      publicationLinks: {},
    }),
  );
  assert.match(html, /Результат передачи неизвестен/);
  assert.match(html, /Привязать и проверить/);
  assert.match(html, /Я проверил в кабинете Prom/);
  const startButton = html
    .match(/<button[^>]*>[^]*?Обновить Prom[^]*?<\/button>/g)
    ?.at(-1);
  assert.ok(startButton);
  assert.match(
    startButton.slice(startButton.lastIndexOf("<button")),
    / disabled/,
  );
  assert.doesNotMatch(html, /Повторить отправку|Контент подтверждён/);
});

test("active import locks source replacement without exposing stored source URL", async () => {
  const html = await renderToString(
    createSSRApp(Form, {
      feed: {
        id: "feed",
        revision: 3,
        enabled: true,
        publicUrl: "https://tenant.example/feed?token=secret",
      },
      busy: false,
      locked: true,
      savedVersion: 0,
    }),
  );
  assert.match(html, /Источник можно заменить после завершения импорта/);
  assert.match(html, /disabled/);
  assert.doesNotMatch(html, /token=secret/);
});
