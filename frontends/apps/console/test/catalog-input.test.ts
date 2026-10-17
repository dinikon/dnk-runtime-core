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
