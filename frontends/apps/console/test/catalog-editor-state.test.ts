import { test } from "node:test";
import assert from "node:assert/strict";
import {
  productEditorGroup,
  productEditorTab,
} from "../src/modules/catalog/model/product-editor-state.ts";
import { catalogRoutes } from "../src/modules/catalog/routes.ts";

test("editor tabs only expose sections available to the product", () => {
  assert.equal(productEditorTab("variants", true), "variants");
  assert.equal(productEditorTab("variants", false), "description");
  assert.equal(productEditorTab("publications", false), "publications");
  assert.equal(productEditorTab("publications", false, false), "description");
  assert.equal(productEditorTab("media", false, false), "media");
  for (const value of [undefined, "general", "unknown", ["variants"]]) {
    assert.equal(productEditorTab(value, true), "description");
  }
});

test("old section links still target editable fields", () => {
  assert.equal(productEditorGroup("general"), "identity");
  assert.equal(productEditorGroup("inventory"), "stock");
  assert.equal(productEditorGroup("shipping"), "measurements");
  assert.equal(productEditorGroup("variants"), undefined);
});

test("old edit links redirect to the single editor without losing view context", () => {
  const route = catalogRoutes.find(
    (route) => route.path === "catalog/items/:itemId/edit",
  );
  assert.equal(typeof route?.redirect, "function");
  if (typeof route?.redirect !== "function") return;
  const query = {
    locale: "uk",
    tab: "variants",
    variant: "v-1",
    focus: "title",
  };
  const result = route.redirect({
    params: { itemId: "product / №1" },
    query,
    hash: "#section",
  } as Parameters<typeof route.redirect>[0]);
  assert.deepEqual(result, {
    path: "/catalog/items/product%20%2F%20%E2%84%961",
    query,
    hash: "#section",
  });
});
