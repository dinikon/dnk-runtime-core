import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { createServer, type ViteDevServer } from "vite";
import vue from "@vitejs/plugin-vue";
import { createSSRApp, type Component } from "vue";
import { renderToString } from "vue/server-renderer";
import {
  mapBindingStock,
  refreshStockPayload,
  exportStockPayload,
} from "../src/modules/channels/api/stock.mapper.ts";
let stockKeys: typeof import("../src/modules/channels/model/stock.query-keys.ts").stockKeys;
import { stockActive } from "../src/modules/channels/model/stock.types.ts";
import { updatePayload } from "../src/modules/channels/api/channel.mapper.ts";

const dto = {
  allow_stock_export: false,
  items: [
    {
      publication_id: "pub",
      stock_owner_id: "pub",
      catalog_position_id: "product",
      catalog_owner_id: "product",
      catalog_quantity: 0,
      publication_quantity: "9007199254740993",
      publication_availability: "in_stock",
      export_blocker: "stock_export_forbidden",
      operation: {
        publication_id: "pub",
        operation_id: "op",
        direction: "read" as const,
        status: "completed" as const,
        quantity: "9007199254740993",
        availability: "in_stock",
        observed_at: "2026-10-29T10:00:00Z",
        desired_quantity: null,
        error_code: null,
        updated_at: "2026-10-29T10:00:00Z",
        recovery_required: false,
      },
    },
  ],
};
test("stock mapping preserves zero, decimal strings and ownership", () => {
  const value = mapBindingStock(dto);
  assert.equal(value.items[0]?.catalogQuantity, 0);
  assert.equal(value.items[0]?.publicationQuantity, "9007199254740993");
  assert.equal(value.items[0]?.ownerId, "pub");
});
test("stock requests copy explicit selection without quantities or secrets", () => {
  const input = { channelId: "c", groupId: "g", publicationIds: ["a", "b"] };
  const payload = refreshStockPayload(input);
  input.publicationIds.push("c");
  assert.deepEqual(payload, { publication_ids: ["a", "b"] });
  assert.deepEqual(exportStockPayload(input), {
    publication_ids: ["a", "b", "c"],
  });
  assert.doesNotMatch(JSON.stringify(payload), /quantity|catalog|credentials/);
});
test("query keys isolate tenants, sessions and groups, polling stops on completion", () => {
  assert.notDeepEqual(
    stockKeys.group(["tenant1", "user", "1"], "c", "g"),
    stockKeys.group(["tenant2", "user", "1"], "c", "g"),
  );
  assert.notDeepEqual(
    stockKeys.group(["t", "u", "1"], "c", "g"),
    stockKeys.group(["t", "u", "2"], "c", "g"),
  );
  assert.notDeepEqual(
    stockKeys.group(["t", "u", "1"], "c", "g"),
    stockKeys.group(["t", "u", "1"], "c", "other"),
  );
  assert.equal(stockActive(mapBindingStock(dto)), false);
  const active = mapBindingStock(dto);
  active.items[0]!.operation!.status = "running";
  assert.equal(stockActive(active), true);
});
test("export permission is nested in typed connection settings and preserves explicit false", () => {
  const config = {
    version: 1,
    endpoint: "https://shop.example",
    settings: {
      currency: "UAH",
      locale: "uk",
      stock_sync: { allow_export: false },
    },
  };
  const payload = updatePayload(
    {
      name: "Woo",
      platformKind: "woocommerce",
      config,
    },
    4,
  );
  assert.equal(payload.config.settings.stock_sync.allow_export, false);
  assert.equal("allow_stock_export" in payload, false);
  assert.deepEqual(payload.config, config);
  assert.equal("allow_stock_export" in payload.config.settings, false);
});
let server: ViteDevServer;
let Panel: Component;
let Actions: Component;
before(async () => {
  server = await createServer({
    configFile: false,
    plugins: [vue()],
    cacheDir: `/tmp/channels-stock-tests-${process.pid}`,
    optimizeDeps: { noDiscovery: true, include: [] },
    resolve: {
      alias: { "@": fileURLToPath(new URL("../src", import.meta.url)) },
    },
    server: { middlewareMode: true, watch: null, ws: false },
    appType: "custom",
  });
  Actions = (
    await server.ssrLoadModule(
      "/src/modules/channels/ui/PublicationActions.vue",
    )
  ).default;
  stockKeys = (
    await server.ssrLoadModule(
      "/src/modules/channels/model/stock.query-keys.ts",
    )
  ).stockKeys;
  Panel = (
    await server.ssrLoadModule(
      "/src/modules/channels/ui/bindings/BindingStockPanel.vue",
    )
  ).default;
});
after(async () => {
  await server?.close();
});
function render(props: Record<string, unknown> = {}): Promise<string> {
  return renderToString(
    createSSRApp(Panel, {
      group: { preview: { publications: [{ id: "pub", title: "Товар" }] } },
      state: mapBindingStock(dto),
      loading: false,
      busy: false,
      error: "",
      selected: ["pub"],
      ...props,
    }),
  ).then((html) => html.replace(/<!--[\s\S]*?-->/g, ""));
}
test("permission disables export and keeps refresh available", async () => {
  const html = await render();
  assert.match(html, /Получение обновляет только публикацию/);
  assert.match(html, /Отправка остатков запрещена/);
  assert.match(
    html,
    /<button[^>]*\sdisabled(?=[\s=>])[^>]*>\s*Отправить остаток\s*<\/button>/,
  );
  assert.match(
    html,
    /<button(?![^>]*\sdisabled(?=[\s=>]))[^>]*>\s*Обновить остаток\s*<\/button>/,
  );
});
test("pending operation prevents duplicate submission and retains quantities", async () => {
  const state = mapBindingStock(dto);
  state.items[0]!.operation!.status = "running";
  const html = await render({ state });
  assert.match(html, /Синхронизация выполняется/);
  assert.match(html, /9007199254740993/);
  assert.match(
    html,
    /<button[^>]*\sdisabled(?=[\s=>])[^>]*>\s*Обновить остаток\s*<\/button>/,
  );
});
test("failed operation and query error retain last quantity and offer retry", async () => {
  const state = mapBindingStock(dto);
  state.items[0]!.operation!.status = "failed";
  state.items[0]!.operation!.errorCode = "stock_job_interrupted";
  const html = await render({ state, error: "Не удалось обновить" });
  assert.match(html, /Повторить/);
  assert.match(html, /Выполнение прервано/);
  assert.match(html, /9007199254740993/);
});
test("loading does not invent quantities or enable actions", async () => {
  const html = await render({ state: undefined, loading: true });
  assert.match(html, /aria-busy="true"/);
  assert.doesNotMatch(html, /Обновить остаток|Отправить остаток|Неизвестно/);
});

test("unconfirmed stock explains quantity and availability without reporting a rejection", async () => {
  const state = mapBindingStock(dto);
  state.items[0]!.operation!.status = "failed";
  state.items[0]!.operation!.errorCode = "stock_write_unconfirmed";
  const html = await render({ state });
  assert.match(
    html,
    /Площадка пока не подтвердила остаток или наличие после отправки/,
  );
  assert.doesNotMatch(html, /Площадка отклонила изменение остатка/);
  assert.match(html, /Повторить действие/);
});

test("stock action is available inside the pinned action group and respects busy state", async () => {
  const html = await renderToString(
    createSSRApp(Actions, {
      catalogTargets: [],
      unlinkTargets: [],
      canSyncStock: true,
      busy: true,
    }),
  );
  const stockButton = html.match(
    /<button[^>]*aria-label="Синхронизация остатков"[^>]*>/,
  )?.[0];
  assert.ok(stockButton);
  assert.match(stockButton, /\sdisabled(?=[\s=>])/);
  const hidden = await renderToString(
    createSSRApp(Actions, { catalogTargets: [], unlinkTargets: [] }),
  );
  assert.doesNotMatch(hidden, /aria-label="Синхронизация остатков"/);
});
