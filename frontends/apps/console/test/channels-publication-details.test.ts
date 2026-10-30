import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { createServer, type ViteDevServer } from "vite";
import vue from "@vitejs/plugin-vue";
import { createSSRApp, type Component } from "vue";
import { renderToString } from "vue/server-renderer";
import type {
  PublicationCard,
  PublicationItem,
} from "../src/modules/channels/model/publication.types.ts";

let server: ViteDevServer;
let Body: Component;
let Table: Component;
before(async () => {
  server = await createServer({
    configFile: false,
    plugins: [vue()],
    resolve: {
      alias: { "@": fileURLToPath(new URL("../src", import.meta.url)) },
    },
    server: { middlewareMode: true, watch: null, ws: false },
    appType: "custom",
  });
  Body = (
    await server.ssrLoadModule(
      "/src/modules/channels/ui/PublicationDetailsBody.vue",
    )
  ).default;
  Table = (
    await server.ssrLoadModule("/src/modules/channels/ui/PublicationsTable.vue")
  ).default;
});
after(async () => {
  await server?.close();
});
const item: PublicationItem = {
  id: "root",
  externalId: "101",
  kind: "simple",
  title: "Основной товар",
  sku: "SKU-BASE",
  url: "https://shop.example/product",
  mainImageUrl: null,
  price: "999999.000000001",
  regularPrice: null,
  salePrice: null,
  currency: "UAH",
  quantity: "0",
  stockMode: "own",
  stockSourcePublicationId: "root",
  availability: "out_of_stock",
  status: "published",
  lastSeenAt: "2026-10-28T10:00:00Z",
  staleConfiguration: false,
};
const variant: PublicationItem = {
  ...item,
  id: "child",
  kind: "variant",
  title: null,
  sku: "SKU-CHILD",
  externalId: "102",
  quantity: null,
  stockMode: "parent",
  staleConfiguration: true,
};
const card: PublicationCard = {
  id: "root",
  rootKind: "simple",
  bindings: [],
  rootExternalId: "201",
  rootSku: "PARENT",
  rootMainImageUrl: "https://cdn.example/parent.jpg",
  title: "Карточка товара",
  selectedPublicationId: "child",
  items: [item, variant],
  minPrice: item.price,
  maxPrice: item.price,
  currency: "UAH",
  lastSeenAt: item.lastSeenAt,
};
async function render(
  value: PublicationCard,
  requestedPublicationId = "root",
): Promise<string> {
  return renderToString(
    createSSRApp(Body, {
      card: value,
      pending: false,
      error: "",
      requestedPublicationId,
    }),
  );
}
test("Prom renders all sellable positions, primary marker and direct-link highlight without Select", async () => {
  const html = await render(card, "child");
  assert.equal((html.match(/data-row-key=/g) ?? []).length, 2);
  assert.match(html, /Позиции публикации/);
  assert.match(html, /Основная позиция/);
  assert.match(html, /SKU-BASE/);
  assert.match(html, /SKU-CHILD/);
  assert.match(html, /aria-current="true"/);
  assert.match(html, /Позиция из ссылки/);
  assert.doesNotMatch(html, /role="combobox"/);
  assert.match(html, /999999\.000000001 UAH/);
  assert.match(html, /Перевод не получен/);
  assert.match(html, /Общий остаток карточки/);
  assert.match(html, /Обычная цена/);
  assert.match(html, /Акционная цена/);
  assert.match(html, /предыдущими настройками/);
});
test("WooCommerce renders a single variation under Variants and never injects the parent", async () => {
  const html = await render({
    ...card,
    rootKind: "variable",
    bindings: [],
    items: [variant],
  });
  assert.match(html, /aria-label="Варианты"/);
  assert.equal((html.match(/data-row-key=/g) ?? []).length, 1);
  assert.doesNotMatch(html, /SKU-BASE|Основная позиция/);
  const empty = await render({
    ...card,
    rootKind: "variable",
    bindings: [],
    items: [],
  });
  assert.match(empty, /Разновидности этой карточки ещё не получены/);
});
test("Simple publication renders one table row, unknown values and safe links", async () => {
  const html = await render({
    ...card,
    items: [
      {
        ...item,
        price: null,
        quantity: null,
        url: "javascript:alert(1)",
        mainImageUrl: "invalid",
      },
    ],
  });
  assert.equal((html.match(/data-row-key=/g) ?? []).length, 1);
  assert.doesNotMatch(html, /aria-label="Варианты"|javascript:|src="invalid"/);
  assert.match(html, /Не получена/);
  assert.match(html, /Не получен/);
});

test("WooCommerce list displays the parent SKU or parent external ID, without leaking the first variant SKU", async () => {
  const parentCard = {
    ...card,
    rootKind: "variable",
    bindings: [],
    items: [variant],
  };
  const html = await renderToString(
    createSSRApp(Table, { items: [parentCard] }),
  );
  assert.match(html, /PARENT/);
  assert.doesNotMatch(html, /SKU-CHILD/);
  for (const rootSku of [null, "", "   "]) {
    const missing = await renderToString(
      createSSRApp(Table, {
        items: [{ ...parentCard, rootSku }],
      }),
    );
    assert.match(missing, />201</);
    assert.doesNotMatch(missing, /SKU-CHILD/);
  }
});
