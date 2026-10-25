import { test } from "node:test";
import assert from "node:assert/strict";
import {
  lineTotal,
  basketPreview,
  newBasketLine,
  cloneSaleValue,
  rebaseSavedSale,
  emptySaleDraft,
  saleDraftFingerprint,
} from "../src/modules/crm/model/sales.draft.ts";

test("CRM money rounds each line half-up, preserves zero and six decimal quantities", () => {
  const row = {
    ...newBasketLine(),
    name: "Услуга",
    quantity: "1.5",
    unitPrice: "10.01",
  };
  assert.equal(lineTotal(row), "15.02");
  assert.equal(
    lineTotal({ ...row, quantity: "0.125", unitPrice: "0" }),
    "0.00",
  );
  assert.equal(
    basketPreview([
      { ...row, quantity: "0.5", unitPrice: "0.01" },
      { ...row, quantity: "0.5", unitPrice: "0.01" },
    ]),
    "0.02",
  );
  assert.equal(
    lineTotal({ ...row, quantity: "0,000001", unitPrice: "999999999999" }),
    "1000000.00",
  );
});
test("CRM totals retain precision above floating point integer range", () => {
  const row = {
    ...newBasketLine(),
    quantity: "999999999999",
    unitPrice: "999999999999",
  };
  assert.equal(
    basketPreview(Array.from({ length: 200 }, () => ({ ...row }))),
    String(999999999999n ** 2n * 200n) + ".00",
  );
});
test("Incomplete prices, zero quantities and excessive precision are invalid", () => {
  for (const [quantity, unitPrice] of [
    ["1", ""],
    ["0", "1"],
    ["1", "-1"],
    ["1.0000001", "1"],
    ["NaN", "1"],
  ])
    assert.throws(() => lineTotal({ ...newBasketLine(), quantity, unitPrice }));
});
test("Cloned form data does not share basket fields or points", () => {
  const value = {
    items: [{ ...newBasketLine(), customFields: { note: "source" } }],
    points: { emails: [{ value: "a@example.com" }] },
  };
  const copy = cloneSaleValue(value);
  copy.items[0]!.customFields.note = "copy";
  copy.points.emails[0]!.value = "b@example.com";
  assert.equal(value.items[0]!.customFields.note, "source");
  assert.equal(value.points.emails[0]!.value, "a@example.com");
});

test("Save acknowledgement preserves later row input and distinct server IDs for duplicate products", () => {
  const sent = emptySaleDraft("f", "EUR");
  sent.title = "Sent";
  sent.items = [
    {
      ...newBasketLine(),
      name: "Same",
      catalogItemId: "product",
      quantity: "1.5",
      unitPrice: "10.01",
    },
    {
      ...newBasketLine(),
      name: "Same",
      catalogItemId: "product",
      quantity: "1.5",
      unitPrice: "10.01",
    },
  ];
  const current = cloneSaleValue(sent);
  current.items[0]!.quantity = "2";
  current.items[1]!.customFields = { note: "Typed after submit" };
  const saved = cloneSaleValue(sent);
  saved.basketRevision = 2;
  saved.items = saved.items.map((row, index) => ({
    ...row,
    id: "server-" + index,
    clientLineKey: "server-" + index,
    quantity: "1.500000",
    unitPrice: "10.010000",
    sku: "SERVER-SKU",
    kind: "service",
  }));
  const result = rebaseSavedSale(
    current,
    sent,
    saved,
    Object.fromEntries(
      sent.items.map((row, index) => [row.clientLineKey, "server-" + index]),
    ),
  );
  assert.equal(result.items[0]!.id, "server-0");
  assert.equal(result.items[1]!.id, "server-1");
  assert.equal(result.items[0]!.clientLineKey, sent.items[0]!.clientLineKey);
  assert.equal(result.items[0]!.quantity, "2");
  assert.equal(result.items[0]!.unitPrice, "10.010000");
  assert.equal(result.items[0]!.sku, "SERVER-SKU");
  assert.equal(result.items[0]!.kind, "service");
  assert.deepEqual(result.items[1]!.customFields, {
    note: "Typed after submit",
  });
  assert.equal(result.basketRevision, 2);
});

test("Server acknowledgement clears dirtiness while keeping local row rendering identity", () => {
  const sent = emptySaleDraft("f", "UAH");
  sent.items = [{ ...newBasketLine(), name: "Row", unitPrice: "0" }];
  const saved = cloneSaleValue(sent);
  saved.basketRevision = 2;
  saved.items = [
    {
      id: "server-id",
      ...saved.items[0]!,
      clientLineKey: "server-id",
      quantity: "1.000000",
      unitPrice: "0.000000",
      lineTotal: "0.00",
    },
  ];
  const next = rebaseSavedSale(sent, sent, saved, {
    [sent.items[0]!.clientLineKey]: "server-id",
  });
  assert.equal(next.items[0]!.clientLineKey, sent.items[0]!.clientLineKey);
  assert.equal(saleDraftFingerprint(next), saleDraftFingerprint(saved));
});
