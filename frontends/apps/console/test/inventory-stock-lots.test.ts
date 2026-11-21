import assert from "node:assert/strict";
import test from "node:test";
import {
  stockLotFromDto,
  stockLotCreateToDto,
  stockLotsPageFromDto,
  stockLotsParamsToDto,
} from "../src/modules/inventory/api/stock-lot.mapper.ts";
import {
  allowsStockLots,
  validCalendarDate,
  validateStockLot,
  displayStockDate,
} from "../src/modules/inventory/model/stock-lot.validation.ts";
import {
  parseStockLotsParams,
  stockLotsListParams,
  stockLotsUrlParams,
} from "../src/modules/inventory/model/stock-lots-page-state.ts";
import { stockLotKeys } from "../src/modules/inventory/model/stock-lot.query-keys.ts";
import { stockLotsReturnPath } from "../src/modules/inventory/model/stock-lot-navigation.ts";
import {
  StockLotRequestError,
  retryStockLots,
} from "../src/modules/inventory/model/stock-lot.errors.ts";
const values = {
  number: " 000Lot-a ",
  manufacturedOn: "2024-02-29",
  expiresOn: "",
};
const dto = {
  id: "lot",
  inventory_item_id: "item",
  number: "000Lot-a",
  manufactured_on: "2024-02-29",
  expires_on: null,
};
test("mapper сохраняет номер, ведущие нули и календарные даты", () => {
  assert.deepEqual(stockLotCreateToDto(values), {
    number: " 000Lot-a ",
    manufactured_on: "2024-02-29",
    expires_on: null,
  });
  assert.deepEqual(stockLotFromDto(dto), {
    id: "lot",
    inventoryItemId: "item",
    number: "000Lot-a",
    manufacturedOn: "2024-02-29",
    expiresOn: null,
  });
  assert.equal(
    stockLotsPageFromDto({ items: [dto], total: 51, offset: 50, limit: 50 })
      .total,
    51,
  );
  assert.equal(displayStockDate("2024-02-29"), "29.02.2024");
  assert.equal(displayStockDate(null), "—");
});
test("даты проверяются календарно без timezone и Date", () => {
  for (const date of ["0001-01-01", "2024-02-29", "2000-02-29", "9999-12-31"])
    assert.equal(validCalendarDate(date), true, date);
  for (const date of [
    "0000-01-01",
    "2023-02-29",
    "1900-02-29",
    "2024-04-31",
    "2024-13-01",
    "2024-01-00",
    "2024-1-01",
    "2024-01-01T00:00:00Z",
  ])
    assert.equal(validCalendarDate(date), false, date);
});
test("форма следует правилам Domain; REQUIRED допускает отсутствие срока", () => {
  assert.deepEqual(
    validateStockLot({ ...values, manufacturedOn: "" }, "REQUIRED"),
    {},
  );
  assert.deepEqual(
    validateStockLot({ ...values, expiresOn: "2024-02-29" }, "OPTIONAL"),
    {},
  );
  assert.ok(
    validateStockLot({ ...values, expiresOn: "2024-02-28" }, "OPTIONAL")
      .expiresOn,
  );
  assert.ok(
    validateStockLot({ ...values, expiresOn: "2024-02-29" }, "NONE").expiresOn,
  );
  for (const number of ["A\u200b", " "])
    assert.ok(validateStockLot({ ...values, number }, "OPTIONAL").number);
  assert.equal(allowsStockLots("NONE"), false);
  assert.equal(allowsStockLots("SERIAL"), false);
  assert.equal(allowsStockLots("LOT"), true);
  assert.equal(allowsStockLots("LOT_AND_SERIAL"), true);
});
test("URL и пагинация сохраняют регистр поиска", () => {
  const parsed = parseStockLotsParams({
    search: " 000Lot-a ",
    page: "2",
    limit: "20",
  });
  assert.deepEqual(parsed, { search: "000Lot-a", page: 2, limit: 20 });
  assert.deepEqual(stockLotsListParams(parsed), {
    search: "000Lot-a",
    offset: 20,
    limit: 20,
  });
  assert.deepEqual(stockLotsUrlParams(parsed), {
    search: "000Lot-a",
    page: "2",
    limit: "20",
  });
  assert.deepEqual(
    stockLotsParamsToDto({ search: " ", offset: 0, limit: 50 }),
    { search: undefined, offset: 0, limit: 50 },
  );
  assert.deepEqual(parseStockLotsParams({ page: "-9", limit: "999" }), {
    search: "",
    page: 1,
    limit: 50,
  });
});
test("query keys изолируют tenant/session, SKU, параметры и партии", () => {
  const key = stockLotKeys.list(["tenant", "user", "1"], "item", {
    search: "000A",
    offset: 0,
    limit: 50,
  });
  for (const scope of [
    ["other", "user", "1"],
    ["tenant", "other", "1"],
    ["tenant", "user", "2"],
  ] as const)
    assert.notDeepEqual(key, stockLotKeys.list(scope, "item", key[7]));
  assert.notDeepEqual(
    key,
    stockLotKeys.list(["tenant", "user", "1"], "other-item", key[7]),
  );
  assert.notDeepEqual(
    key,
    stockLotKeys.list(["tenant", "user", "1"], "item", {
      ...key[7],
      offset: 50,
    }),
  );
});
test("returnTo допускает только собственный список или карточку SKU", () => {
  const own = "/inventory/items/item/lots?search=000A&page=2#table";
  assert.equal(stockLotsReturnPath("item", own, true), own);
  for (const value of [
    "https://evil.example",
    "//evil.example",
    "/inventory/items/other/lots",
    own + "\n",
    own + "\\path",
  ])
    assert.equal(
      stockLotsReturnPath("item", value, true),
      "/inventory/items/item/lots",
    );
  const parent = "/inventory/items/item?returnTo=%2Finventory%2Fitems";
  assert.equal(stockLotsReturnPath("item", parent), parent);
});
test("неоднозначный POST отличается от отказа, чтение не повторяет 4xx", () => {
  for (const status of [null, 408, 500, 503])
    assert.equal(new StockLotRequestError("failed", status).uncertain, true);
  for (const status of [403, 404, 409, 422]) {
    const error = new StockLotRequestError("rejected", status);
    assert.equal(error.uncertain, false);
    assert.equal(retryStockLots(0, error), false);
  }
  assert.equal(retryStockLots(0, new Error("offline")), true);
  assert.equal(retryStockLots(1, new Error("offline")), false);
});
