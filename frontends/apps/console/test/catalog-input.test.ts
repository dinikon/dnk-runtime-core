import { sectionError } from "../src/modules/catalog/model/product-validation.ts";
import { test } from "node:test";
import assert from "node:assert/strict";
import { decimalInput } from "../src/modules/catalog/model/product-input.ts";
import { convertMeasurement } from "../src/modules/catalog/model/measurement-conversion.ts";

test("locale decimal keyboard preserves exact strings and measurement magnitude", () => {
  assert.equal(
    decimalInput("9007199254740993,000001"),
    "9007199254740993.000001",
  );
  assert.equal(decimalInput("0,000001"), "0.000001");
  assert.equal(
    convertMeasurement(decimalInput("1,234567"), "kg", "g"),
    "1234.567",
  );
  assert.equal(decimalInput(0), "0");
  assert.equal(decimalInput("-0,1"), "-0.1");
  assert.equal(decimalInput(""), "");
});

test("purchase is independent and the server resolves non-discounted sale amounts", () => {
  assert.equal(sectionError("purchase_price", { purchase_price: "0" }), "");
  assert.equal(sectionError("purchase_price", { purchase_price: null }), "");
  assert.notEqual(sectionError("purchase_price", { purchase_price: "-1" }), "");
  const patch = {
    purchase_price: "300",
    price_specification: {
      regular_price: "200",
      sale_price: "199.999999",
      date_on_sale_from: null,
      date_on_sale_to: null,
    },
  };
  assert.equal(sectionError("price", patch), "");
  patch.price_specification.sale_price = "200.000000";
  assert.equal(sectionError("price", patch), "");
  patch.price_specification.sale_price = "201";
  assert.equal(sectionError("price", patch), "");
  patch.price_specification.sale_price = "-1";
  assert.notEqual(sectionError("price", patch), "");
});
