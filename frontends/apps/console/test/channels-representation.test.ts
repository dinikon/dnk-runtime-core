import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { createServer, type ViteDevServer } from "vite";
import vue from "@vitejs/plugin-vue";
import { createSSRApp, type Component } from "vue";
import { renderToString } from "vue/server-renderer";
import type { PreviewRepresentationResponseDto } from "../src/modules/channels/api/representation.dto.ts";
import {
  representationPreview,
  representationDraftPayload,
  representationDetails,
} from "../src/modules/channels/api/representation.mapper.ts";
import {
  normalizeRepresentationOverrides,
  representationDraftKey,
} from "../src/modules/channels/model/representation.draft.ts";

function fixture(): PreviewRepresentationResponseDto {
  const origin = { kind: "catalog" as const, catalog_position_id: "product" };
  return {
    state: {
      id: null,
      revision: 0,
      export_enabled: false,
      overrides: { common: {}, items: {} },
      created_at: null,
      updated_at: null,
      created_by: null,
      updated_by: null,
    },
    export_blockers: ["representation_title_missing"],
    draft: false,
    representation: {
      channel_id: "channel",
      connection_id: "connection",
      binding_group_id: "group",
      binding_revision: 2,
      config_revision: 3,
      platform: "prom",
      mode: "SIMPLE_TO_SIMPLE",
      locales: ["uk", "ru"],
      as_of: "2026-10-30T12:00:00Z",
      binding_state: "linked",
      issues: [],
      targets: [
        {
          publication_id: "publication",
          external_id: "101",
          parent_publication_id: null,
          publication_kind: "simple",
          binding_item_id: "pair",
          catalog_position_id: "product",
          role: "position",
          catalog_content: [
            {
              locale: "uk",
              title: "Catalog source",
              body: "Source body",
              gallery: [],
              origins: { title: origin, body: origin, gallery: origin },
            },
          ],
          ready: false,
          issues: [
            {
              code: "representation_title_missing",
              field: "title",
              locale: "ru",
              publication_id: "publication",
            },
          ],
          content: [
            {
              locale: "uk",
              title: "Назва",
              body: "",
              gallery: [],
              origins: { title: origin, body: origin, gallery: origin },
            },
            {
              locale: "ru",
              title: null,
              body: null,
              gallery: null,
              origins: {
                title: { kind: "missing", catalog_position_id: null },
                body: { kind: "missing", catalog_position_id: null },
                gallery: { kind: "missing", catalog_position_id: null },
              },
            },
          ],
        },
      ],
    },
  };
}

test("mapping preserves locales, stable pair IDs, missing and explicitly cleared fields", () => {
  const dto = fixture();
  const value = representationPreview(dto);
  assert.equal(value.targets[0]?.catalogContent[0]?.title, "Catalog source");
  assert.deepEqual(value.exportBlockers, ["representation_title_missing"]);
  assert.equal(value.targets[0]?.bindingItemId, "pair");
  assert.equal(value.targets[0]?.content[0]?.body, "");
  assert.deepEqual(value.targets[0]?.content[0]?.gallery, []);
  assert.equal(value.targets[0]?.content[1]?.body, null);
  assert.equal(value.targets[0]?.content[1]?.gallery, null);
  assert.equal(
    value.targets[0]?.content[0]?.origins.title.catalogPositionId,
    "product",
  );
  dto.representation.locales.reverse();
  dto.representation.targets[0]!.content[0]!.origins.title.catalog_position_id =
    "changed";
  assert.deepEqual(value.locales, ["uk", "ru"]);
  assert.equal(
    value.targets[0]?.content[0]?.origins.title.catalogPositionId,
    "product",
  );
});

test("complete override payload keeps revisions, independent languages and explicit clears", () => {
  const overrides = {
    common: { uk: { title: "Group", body: null }, ru: { body: "" } },
    items: { pair: { uk: { gallery: [] } } },
  };
  const payload = representationDraftPayload({
    expectedRevision: 0,
    expectedBindingRevision: 2,
    expectedConfigRevision: 3,
    overrides,
  });
  assert.deepEqual(payload, {
    expected_revision: 0,
    expected_binding_revision: 2,
    expected_config_revision: 3,
    overrides: {
      common: { uk: { title: "Group" }, ru: { body: "" } },
      items: { pair: { uk: { gallery: [] } } },
    },
  });
  overrides.common.uk.title = "Typed while saving";
  assert.equal(payload.overrides.common.uk?.title, "Group");
  assert.doesNotMatch(
    JSON.stringify(payload),
    /export_enabled|channel_id|credentials/,
  );
});

test("draft normalization removes only inheritance and isolates gallery edits", () => {
  const gallery = [{ fileId: "file", alt: "A", caption: "B" }];
  const input = {
    common: { ru: {}, uk: { title: null, gallery } },
    items: { removed: { uk: {} }, pair: { ru: { body: "", gallery: [] } } },
  };
  const draft = normalizeRepresentationOverrides(input);
  gallery[0]!.alt = "Changed";
  assert.equal(draft.common.uk?.gallery?.[0]?.alt, "A");
  assert.equal("ru" in draft.common, false);
  assert.equal("removed" in draft.items, false);
  assert.equal(draft.items.pair?.ru?.body, "");
  assert.deepEqual(draft.items.pair?.ru?.gallery, []);
  assert.equal(
    representationDraftKey({ common: { ru: {}, uk: {} }, items: {} }),
    representationDraftKey({ common: {}, items: {} }),
  );
});

test("saved state mapping preserves permissions, revision zero and stable binding items", () => {
  const value = representationDetails({
    state: {
      id: null,
      revision: 0,
      export_enabled: false,
      overrides: { common: {}, items: {} },
      created_at: null,
      updated_at: null,
      created_by: null,
      updated_by: null,
    },
    binding_revision: 7,
    config_revision: 3,
    locales: ["uk"],
    items: [
      {
        id: "pair",
        catalog_position_id: "catalog",
        publication_id: "publication",
      },
    ],
  });
  assert.equal(value.state.revision, 0);
  assert.equal(value.state.exportEnabled, false);
  assert.equal(value.bindingRevision, 7);
  assert.deepEqual(value.items, [
    { id: "pair", catalogPositionId: "catalog", publicationId: "publication" },
  ]);
});

let server: ViteDevServer;
let Panel: Component;
let keys: typeof import("../src/modules/channels/model/representation.query-keys.ts").representationKeys;
before(async () => {
  server = await createServer({
    configFile: false,
    plugins: [vue()],
    cacheDir: `/tmp/channels-representation-tests-${process.pid}`,
    optimizeDeps: { noDiscovery: true, include: [] },
    resolve: {
      alias: { "@": fileURLToPath(new URL("../src", import.meta.url)) },
    },
    server: { middlewareMode: true, watch: null, ws: false },
    appType: "custom",
  });
  Panel = (
    await server.ssrLoadModule(
      "/src/modules/channels/ui/bindings/RepresentationPreviewPanel.vue",
    )
  ).default;
  keys = (
    await server.ssrLoadModule(
      "/src/modules/channels/model/representation.query-keys.ts",
    )
  ).representationKeys;
});
after(async () => {
  await server?.close();
});

function render(props: Record<string, unknown>): Promise<string> {
  return renderToString(
    createSSRApp(Panel, { locale: "uk", loading: false, error: "", ...props }),
  );
}

test("preview cache separates tenant, user session, channel and group", () => {
  const scope = ["tenant", "user", "1"] as const;
  const original = keys.preview(scope, "channel", "group");
  for (const next of [
    keys.preview(["other", "user", "1"], "channel", "group"),
    keys.preview(["tenant", "user", "2"], "channel", "group"),
    keys.preview(scope, "other", "group"),
    keys.preview(scope, "channel", "other"),
  ])
    assert.notDeepEqual(original, next);
});

test("loading, empty result and failed request have explicit states and retry", async () => {
  assert.match(await render({ loading: true }), /Формирование представления/);
  const dto = fixture();
  dto.representation.targets = [];
  assert.match(
    await render({ preview: representationPreview(dto) }),
    /нет сопоставленных позиций/,
  );
  const error = await render({ error: "Не удалось загрузить представление" });
  assert.match(error, /Повторить/);
  assert.doesNotMatch(error, /Формирование представления/);
});

test("background failure retains content, locale diagnostics and distinct empty values", async () => {
  const value = representationPreview(fixture());
  const html = await render({ preview: value, error: "Сеть недоступна" });
  assert.match(html, /Назва/);
  assert.match(html, /Пустое описание/);
  assert.match(html, /Пустая галерея/);
  assert.match(html, /ru:.*не заполнено название/);
  assert.match(html, /Повторить/);
  const ru = await render({ preview: value, locale: "ru" });
  assert.match(ru, /Галерея не задана/);
  assert.doesNotMatch(ru, /Пустое описание/);
});
