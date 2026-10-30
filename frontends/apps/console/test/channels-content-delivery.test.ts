import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { createServer, type ViteDevServer } from "vite";
import vue from "@vitejs/plugin-vue";
import { createSSRApp, type Component } from "vue";
import { renderToString } from "vue/server-renderer";
import {
  contentDelivery,
  contentDeliveryPayload,
  contentReconciliationPayload,
} from "../src/modules/channels/api/content-delivery.mapper.ts";
import { contentDeliverySummary } from "../src/modules/channels/model/content-delivery.display.ts";
let contentDeliveryIssue: (code: string) => string;
import type { ContentDeliveryTargetDto } from "../src/modules/channels/api/content-delivery.dto.ts";

function fixture(): ContentDeliveryTargetDto {
  return {
    publication_id: "pub",
    external_id: "101",
    role: "position",
    publication_kind: "simple",
    revision: 3,
    requested_generation: 2,
    sending_generation: 1,
    applied_generation: 1,
    status: "succeeded",
    confirmed_fields: ["title", "body", "gallery"],
    error_code: null,
    updated_at: "2026-10-30T12:00:00Z",
    completed_at: "2026-10-30T12:00:00Z",
    content_fingerprint: "a".repeat(64),
    recovery_required: false,
  };
}

test("mapping preserves generations and sends exactly preview and concurrency tokens", () => {
  const value = contentDelivery(fixture());
  assert.equal(value.requestedGeneration, 2);
  assert.equal(value.appliedGeneration, 1);
  assert.deepEqual(value.confirmedFields, ["title", "body", "gallery"]);
  assert.deepEqual(
    contentDeliveryPayload({
      channelId: "channel",
      groupId: "group",
      expectedRevision: 2,
      expectedBindingRevision: 3,
      expectedConfigRevision: 4,
      contentFingerprint: "a".repeat(64),
    }),
    {
      expected_revision: 2,
      expected_binding_revision: 3,
      expected_config_revision: 4,
      content_fingerprint: "a".repeat(64),
    },
  );
  assert.deepEqual(
    contentReconciliationPayload({
      channelId: "channel",
      groupId: "group",
      publicationId: "pub",
      expectedRevision: 5,
    }),
    { expected_revision: 5 },
  );
});

test("summary distinguishes empty, active, partial and unresolved outcomes", () => {
  const success = contentDelivery(fixture());
  assert.equal(contentDeliverySummary([]), "Обновление ещё не запускалось");
  assert.equal(contentDeliverySummary([success]), "Все цели обновлены");
  assert.equal(
    contentDeliverySummary([success, { ...success, status: "failed" }]),
    "Обновлено частично",
  );
  assert.equal(
    contentDeliverySummary([{ ...success, status: "queued" }]),
    "Обновление выполняется",
  );
  assert.equal(
    contentDeliverySummary([{ ...success, status: "unknown" }]),
    "Требуется внимание",
  );
  assert.match(
    contentDeliveryIssue("content_reconciliation_required"),
    /Повторная отправка остановлена/,
  );
});

let server: ViteDevServer;
let Panel: Component;
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
  ({ contentDeliveryIssue } = await server.ssrLoadModule(
    "/src/modules/channels/model/content-delivery.errors.ts",
  ));
  Panel = (
    await server.ssrLoadModule(
      "/src/modules/channels/ui/bindings/ContentDeliveriesPanel.vue",
    )
  ).default;
});
after(async () => server?.close());

test("panel renders pending, actionable unknown and partial errors without native payload", async () => {
  const props = {
    items: [],
    loading: true,
    error: "",
    busy: false,
    canRequest: false,
    canReview: false,
    reviewed: false,
    fingerprint: "a".repeat(64),
    issues: [],
    errorMessages: {},
  };
  const loading = await renderToString(createSSRApp(Panel, props));
  assert.match(loading, /Обновление ещё не запускалось/);
  assert.match(loading, /disabled/);
  const unknown = contentDelivery({
    ...fixture(),
    status: "unknown",
    error_code: "network_timeout",
    recovery_required: true,
  });
  const html = await renderToString(
    createSSRApp(Panel, {
      ...props,
      loading: false,
      items: [unknown],
      errorMessages: { pub: contentDeliveryIssue("network_timeout") },
    }),
  );
  assert.match(html, /Сверить с площадкой/);
  assert.match(html, /Перед повтором требуется сверка/);
  assert.doesNotMatch(html, /token=|consumer_secret|prepared_request/);
  const error = await renderToString(
    createSSRApp(Panel, { ...props, error: "Не удалось получить результаты" }),
  );
  assert.match(error, /Не удалось получить результаты/);
  assert.match(error, /Перечитать результат/);
});
