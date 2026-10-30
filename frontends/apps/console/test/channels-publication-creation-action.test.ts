import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { createServer, type ViteDevServer } from "vite";
import vue from "@vitejs/plugin-vue";
import { createSSRApp, type Component } from "vue";
import { renderToString } from "vue/server-renderer";

let server: ViteDevServer;
let Action: Component;
before(async () => {
  server = await createServer({
    configFile: false,
    plugins: [vue()],
    cacheDir: `/tmp/channels-publication-action-${process.pid}`,
    optimizeDeps: { noDiscovery: true, include: [] },
    resolve: {
      alias: { "@": fileURLToPath(new URL("../src", import.meta.url)) },
    },
    server: { middlewareMode: true, watch: null, ws: false },
    appType: "custom",
  });
  Action = (
    await server.ssrLoadModule(
      "/src/modules/channels/ui/PublicationCatalogAction.vue",
    )
  ).default;
});
after(async () => {
  await server?.close();
});
function render(props: Record<string, unknown> = {}): Promise<string> {
  return renderToString(
    createSSRApp(Action, {
      catalogItemId: null,
      pending: false,
      disabled: false,
      error: "",
      warnings: [],
      ...props,
    }),
  );
}
test("An unbound publication offers direct creation without a dialog", async () => {
  const html = await render();
  assert.match(html, /Создать товар/);
  assert.match(html, /Создать связь/);
  assert.match(html, /автоматически свяжется/);
  assert.doesNotMatch(html, /Открыть товар|role="dialog"|\sdisabled(?:=|>|\s)/);
});
test("A linked publication opens its existing Catalog item instead of creating a duplicate", async () => {
  const html = await render({ catalogItemId: "existing-item" });
  assert.match(html, /Открыть товар/);
  assert.doesNotMatch(html, /Создать товар/);
});
test("Creation blocks repeated submits and preserves actionable errors and warnings", async () => {
  const pending = await render({ pending: true });
  assert.match(pending, /Создание…/);
  assert.match(pending, /\sdisabled(?:=|>|\s)/);
  assert.match(pending, /aria-busy="true"/);
  const failed = await render({ error: "Площадка временно недоступна" });
  assert.match(failed, /Площадка временно недоступна/);
  assert.match(failed, /Создать товар/);
  assert.doesNotMatch(failed, /\sdisabled(?:=|>|\s)/);
  const warnings = await render({
    catalogItemId: "created-item",
    warnings: ["SKU не перенесён", "Изображение пропущено"],
  });
  assert.match(warnings, /SKU не перенесён/);
  assert.match(warnings, /Изображение пропущено/);
  assert.match(warnings, /Открыть товар/);
});
