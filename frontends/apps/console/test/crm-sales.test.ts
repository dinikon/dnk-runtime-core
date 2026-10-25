import { test } from "node:test";
import assert from "node:assert/strict";
import {
  lineTotal,
  basketPreview,
  newBasketLine,
  cloneSaleValue,
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
