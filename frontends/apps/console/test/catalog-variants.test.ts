import { test } from "node:test";
import assert from "node:assert/strict";
import { createRenderer, h, ref, nextTick } from "vue";
import { createRouter, createMemoryHistory } from "vue-router";
import { useCatalogVariantsPageState } from "../src/modules/catalog/model/use-catalog-variants-page-state.ts";
import {
  ProductCreation,
  productCreationState,
} from "../src/modules/catalog/model/product-creation.ts";
import { itemFromDto } from "../src/modules/catalog/api/catalog.mapper.ts";
import type { ReadItemDTO } from "../src/modules/catalog/api/catalog.dto.ts";

async function page(url: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/:pathMatch(.*)*", component: { render: () => null } }],
  });
  await router.push(url);
  const root = ref("root"),
    locale = ref("ru");
  let state!: ReturnType<typeof useCatalogVariantsPageState>;
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
      state = useCatalogVariantsPageState(root, locale);
      return () => h("div");
    },
  });
  app.use(router);
  app.mount({});
  async function navigate(action: () => void) {
    await new Promise<void>((resolve) => {
      const stop = router.afterEach(() => {
        stop();
        resolve();
      });
      action();
    });
    await nextTick();
  }
  return { router, root, locale, state, navigate, stop: () => app.unmount() };
}

test("variant URL preserves parent filters when opening, closing and paginating", async () => {
  const p = await page(
    "/catalog/items/root/edit?locale=ru&tab=variants&variant=child&variants_limit=50&variants_offset=50",
  );
  assert.equal(p.state.selected.value, "child");
  assert.deepEqual(p.state.pagination.value, { limit: 50, offset: 50 });
  await p.navigate(() => p.state.close());
  assert.equal(p.router.currentRoute.value.query.variant, undefined);
  assert.equal(p.router.currentRoute.value.query.locale, "ru");
  assert.equal(p.router.currentRoute.value.query.tab, "variants");
  await p.navigate(() => p.state.open("next"));
  assert.equal(p.state.selected.value, "next");
  await p.navigate(() => p.state.setPage({ page: 1, limit: 100 }));
  assert.deepEqual(p.state.pagination.value, { limit: 100, offset: 0 });
  assert.equal(p.state.selected.value, "next");
  p.stop();
});

test("locale resets pagination; changing root clears child selection", async () => {
  const p = await page("/root?locale=ru&variant=old&variants_offset=75");
  await p.navigate(() => {
    p.locale.value = "en";
  });
  assert.equal(p.state.pagination.value.offset, 0);
  assert.equal(p.state.selected.value, "old");
  await p.navigate(() => {
    p.root.value = "other";
  });
  assert.equal(p.state.selected.value, "");
  p.stop();
});

test("invalid pagination is bounded and normalized", async () => {
  for (const [query, expected] of [
    ["variants_limit=200&variants_offset=-50", { limit: 25, offset: 0 }],
    ["variants_limit=50&variants_offset=99", { limit: 50, offset: 50 }],
    ["variants_offset=NaN", { limit: 25, offset: 0 }],
  ] as const) {
    const p = await page("/root?" + query);
    assert.deepEqual(p.state.pagination.value, expected);
    p.stop();
  }
});

test("creating a variable container sends explicit role and never virtual service", async () => {
  const sent: unknown[] = [];
  const creation = new ProductCreation(
    productCreationState(),
    async (virtual, kind) => {
      sent.push({ virtual, kind });
      return { id: "container" };
    },
    async () => {},
    () => ({ message: "error", uncertain: false }),
  );
  await creation.create("variable");
  assert.deepEqual(sent, [{ virtual: false, kind: "variable" }]);
});

test("effective values do not become own overrides or monetary Numbers", () => {
  const dto = {
    id: "child",
    kind: "variant",
    parent_id: "root",
    stock: {
      manage_stock: false,
      stock_quantity: null,
      stock_status: "out_of_stock",
      backorders: "no",
    },
    effective_stock: {
      manage_stock: true,
      stock_quantity: 7,
      stock_status: null,
      backorders: "no",
    },
    content: null,
    effective_content: { title: "Parent" },
    gallery: null,
    price: "123.456789",
    sources: { title: "root", stock: "root" },
  } as ReadItemDTO;
  const result = itemFromDto(dto);
  assert.equal(result.title, "Parent");
  assert.equal(result.content, null);
  assert.equal(result.stock.stock_quantity, null);
  assert.equal(result.stock.stock_status, "out_of_stock");
  assert.equal(result.effective_stock?.stock_quantity, 7);
  assert.equal(result.price, "123.456789");
});

test("stock editor mode follows own quantity, then parent quantity, then manual status", async () => {
  const { stockFormMode } =
    await import("../src/modules/catalog/model/product-presentation.ts");
  const manual = {
    manage_stock: false,
    stock_quantity: null,
    stock_status: "on_backorder",
    backorders: "no",
  } as const;
  const counted = {
    manage_stock: true,
    stock_quantity: 7,
    stock_status: null,
    backorders: "no",
  } as const;
  assert.equal(stockFormMode("simple", manual), "manual");
  assert.equal(stockFormMode("simple", counted), "quantity");
  assert.equal(stockFormMode("variable", manual), "variants");
  assert.equal(stockFormMode("variable", counted), "quantity");
  assert.equal(stockFormMode("variant", manual, manual), "manual");
  assert.equal(stockFormMode("variant", manual, counted), "inherited");
  assert.equal(stockFormMode("variant", counted, counted), "quantity");
  assert.equal(stockFormMode("variant", counted, manual), "quantity");
  assert.equal(manual.stock_status, "on_backorder");
});
