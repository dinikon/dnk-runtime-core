import assert from "node:assert/strict";
import test from "node:test";
import { createRenderer, h, nextTick } from "vue";
import { createRouter, createMemoryHistory } from "vue-router";
import {
  catalogPage,
  parseCatalogItemsParams,
} from "../src/modules/catalog/model/catalog-list-state.ts";
import { useCatalogItemsPageState } from "../src/modules/catalog/model/use-catalog-items-page-state.ts";
import {
  catalogListPrice,
  catalogListStock,
} from "../src/modules/catalog/model/catalog-list.presentation.ts";
import { listItemFromDto } from "../src/modules/catalog/api/catalog.mapper.ts";
import type { CatalogListItem } from "../src/modules/catalog/model/catalog.types.ts";
import type { ListItemDTO } from "../src/modules/catalog/api/catalog.dto.ts";

test("catalog pagination ignores malformed URL values and bounds API offsets", () => {
  for (const input of ["Infinity", "NaN", "", undefined, ["2"], -4])
    assert.equal(catalogPage(input), 1);
  assert.equal(catalogPage("2.9"), 2);
  assert.ok((catalogPage("999999999999999") - 1) * 20 <= 2147483600);
  assert.deepEqual(
    parseCatalogItemsParams({ search: ["bad"], status: "unknown", page: "2" }),
    { search: "", status: undefined, page: 2 },
  );
});

test("catalog price presentation retains zero, decimal precision and variant semantics", () => {
  const item: CatalogListItem = {
    id: "1",
    title: "A",
    sku: null,
    status: "active",
    price: "123456789012345678.123456",
    currency: "USD",
    availableForSale: true,
  };
  assert.equal(catalogListPrice(item), "123456789012345678.123456 USD");
  assert.equal(catalogListPrice({ ...item, price: "0" }), "0 USD");
  assert.equal(catalogListPrice({ ...item, price: null }), "Цена не задана");
  assert.equal(
    catalogListPrice({
      ...item,
      kind: "variable",
      min_price: "0.00",
      max_price: "100.123456",
    }),
    "0–100.123456 USD",
  );
  assert.equal(
    catalogListPrice({
      ...item,
      kind: "variable",
      min_price: "10.0",
      max_price: "10.00",
    }),
    "10 USD",
  );
  assert.equal(
    catalogListPrice({ ...item, kind: "variable", mixed_currencies: true }),
    "Разные валюты",
  );
  assert.equal(
    catalogListPrice({ ...item, kind: "variable", min_price: null }),
    "Цена вариантов не задана",
  );
});

test("list mapper keeps the image, stock status and exact price from the existing API", () => {
  const image = {
    id: "image",
    file_id: "file",
    position: 0,
    alt: "Photo",
    caption: "",
  };
  const dto = {
    id: "1",
    title: "A",
    sku: null,
    kind: "simple",
    parent_id: null,
    variant_count: 0,
    min_price: null,
    max_price: null,
    mixed_currencies: false,
    status: "draft",
    price: "0.123456",
    currency: "USD",
    stock_status: "in_stock",
    manage_stock: true,
    stock_quantity: 0,
    stock_source: "own",
    primary_image: image,
    available_for_sale: false,
    weight: null,
    dimensions: null,
  } satisfies ListItemDTO;
  const item = listItemFromDto(dto);
  assert.equal(item.stockStatus, "in_stock");
  assert.equal(item.manageStock, true);
  assert.equal(item.stockQuantity, 0);
  assert.equal(item.stockSource, "own");
  assert.equal(item.availableForSale, false);
  assert.equal(item.price, "0.123456");
  assert.deepEqual(item.primaryImage, image);
  assert.equal(
    listItemFromDto({ ...dto, stock_status: null, primary_image: null })
      .stockStatus,
    null,
  );
});

test("table stock distinguishes zero, manual availability, variants and a shared source", () => {
  const item: CatalogListItem = {
    id: "root",
    title: "Stock",
    sku: null,
    status: "active",
    price: null,
    currency: null,
    availableForSale: false,
    manageStock: true,
    stockQuantity: 0,
  };
  assert.equal(catalogListStock(item), "0");
  assert.equal(catalogListStock({ ...item, stockQuantity: -2 }), "-2");
  assert.equal(
    catalogListStock({ ...item, kind: "variant", stockSource: "parent" }),
    "0 · общий",
  );
  assert.equal(
    catalogListStock({ ...item, manageStock: false, stockQuantity: null }),
    "Без учёта",
  );
  assert.equal(
    catalogListStock({ ...item, kind: "variable", manageStock: false }),
    "В вариантах",
  );
});

test("catalog URL actions reset pagination and preserve locale, unrelated query and hash", async () => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/:pathMatch(.*)*", component: { render: () => null } }],
  });
  await router.push(
    "/catalog/items?locale=uk&search=old&status=draft&page=3&keep=yes#list",
  );
  let state!: ReturnType<typeof useCatalogItemsPageState>;
  const renderer = createRenderer<object, object>({
    patchProp() {},
    insert() {},
    remove() {},
    setText() {},
    setElementText() {},
    createElement: () => ({}),
    createText: () => ({}),
    createComment: () => ({}),
    parentNode: () => null,
    nextSibling: () => null,
  });
  const app = renderer.createApp({
    setup() {
      state = useCatalogItemsPageState();
      return () => h("div");
    },
  });
  app.use(router);
  app.mount({});
  async function navigate(action: () => void): Promise<void> {
    await new Promise<void>((resolve) => {
      const stop = router.afterEach(() => {
        stop();
        resolve();
      });
      action();
    });
    await nextTick();
  }
  try {
    assert.equal(state.params.value.page, 3);
    await navigate(() => state.status("active"));
    assert.equal(state.params.value.page, 1);
    assert.equal(state.params.value.search, "old");
    await navigate(() => state.search("new SKU"));
    assert.equal(state.params.value.status, "active");
    await navigate(() => state.page(2));
    assert.equal(state.params.value.page, 2);
    await navigate(() => state.clear());
    assert.deepEqual(state.params.value, {
      search: "",
      status: undefined,
      page: 1,
    });
    assert.deepEqual(router.currentRoute.value.query, {
      locale: "uk",
      keep: "yes",
    });
    assert.equal(router.currentRoute.value.hash, "#list");
  } finally {
    app.unmount();
  }
});
