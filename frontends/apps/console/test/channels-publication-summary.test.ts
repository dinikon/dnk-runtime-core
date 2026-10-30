import { test } from "node:test";
import assert from "node:assert/strict";
import {
  publicationPrice,
  publicationStock,
  bindingPublicationPrice,
  bindingPublicationStock,
} from "../src/modules/channels/model/publication-summary.ts";
import type {
  PublicationCard,
  PublicationItem,
} from "../src/modules/channels/model/publication.types.ts";
import type { BindingPosition } from "../src/modules/channels/model/bindings/binding.types.ts";

function item(
  id: string,
  quantity: string | null,
  source = id,
): PublicationItem {
  return {
    id,
    externalId: id,
    kind: "variant",
    title: id,
    sku: null,
    url: null,
    mainImageUrl: null,
    price: "10",
    regularPrice: null,
    salePrice: null,
    currency: "UAH",
    quantity,
    stockMode: source === id ? "own" : "parent",
    stockSourcePublicationId: source,
    availability: null,
    status: null,
    lastSeenAt: "2026-10-29",
    staleConfiguration: false,
  };
}
function card(items: PublicationItem[]): PublicationCard {
  return {
    id: "root",
    rootKind: "variable",
    rootExternalId: "root",
    rootSku: null,
    rootMainImageUrl: null,
    title: "Товар",
    selectedPublicationId: null,
    items,
    bindings: [],
    minPrice: "0",
    maxPrice: "123456789012345678.123456",
    currency: "UAH",
    lastSeenAt: "2026-10-29",
  };
}
function position(
  id: string,
  price: string | null,
  quantity: string | null,
  currency = "UAH",
): BindingPosition {
  return {
    id,
    kind: "simple",
    title: id,
    sku: null,
    imageUrl: null,
    status: null,
    price,
    currency,
    quantity,
    availability: null,
    stockSourceId: id,
    externalId: id,
    stale: false,
  };
}
test("prices keep zero, range and decimal precision without floating point", () => {
  assert.equal(publicationPrice(card([])), "0–123456789012345678.123456 UAH");
  assert.equal(
    bindingPublicationPrice([
      position("a", "123456789012345678.123457", null),
      position("b", "123456789012345678.123456", null),
    ]),
    "123456789012345678.123456–123456789012345678.123457 UAH",
  );
  assert.equal(bindingPublicationPrice([position("zero", "0", null)]), "0 UAH");
});
test("missing prices and mixed currencies are not turned into zero or one currency", () => {
  assert.equal(
    publicationPrice({
      ...card([]),
      minPrice: null,
      maxPrice: null,
      currency: null,
    }),
    "Не получена",
  );
  assert.equal(
    bindingPublicationPrice([
      position("a", "1", null),
      position("b", "2", null, "USD"),
    ]),
    "Разные валюты",
  );
  assert.equal(
    bindingPublicationPrice([position("a", null, null)]),
    "Не получена",
  );
});
test("stocks sum unique sources exactly and never multiply a shared parent stock", () => {
  assert.equal(
    publicationStock(
      card([item("a", "3", "parent"), item("b", "3", "parent")]),
    ),
    "3",
  );
  assert.equal(
    publicationStock(card([item("a", "9007199254740993.1"), item("b", "0.2")])),
    "9007199254740993.3",
  );
  assert.equal(publicationStock(card([item("zero", "0")])), "0");
  assert.equal(
    publicationStock(card([item("a", "1E+2"), item("b", "0E-6")])),
    "100",
  );
});
test("unknown and partial stock are distinguished from a real zero", () => {
  assert.equal(publicationStock(card([item("a", null)])), "Не получен");
  assert.equal(
    publicationStock(card([item("a", "10"), item("b", null)])),
    "Частично получен",
  );
  assert.equal(publicationStock(card([])), "Не получен");
});
test("binding summaries ignore variable containers and preserve shared stock", () => {
  const container = { ...position("root", "999", "100"), kind: "variable" };
  const a = { ...position("a", "1.5", "8"), stockSourceId: "root" };
  const b = { ...position("b", "2.5", "8"), stockSourceId: "root" };
  assert.equal(bindingPublicationPrice([container, a, b]), "1.5–2.5 UAH");
  assert.equal(bindingPublicationStock([container, a, b]), "8");
});
