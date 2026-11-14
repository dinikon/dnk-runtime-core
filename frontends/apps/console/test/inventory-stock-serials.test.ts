import assert from "node:assert/strict";
import test from "node:test";
import { QueryClient } from "@tanstack/vue-query";
import {
  stockSerialCreateToDto,
  stockSerialFromDto,
} from "../src/modules/inventory/api/stock-serial.mapper.ts";
import {
  allowsStockSerials,
  validateStockSerial,
} from "../src/modules/inventory/model/stock-serial.validation.ts";
import { stockSerialKeys } from "../src/modules/inventory/model/stock-serial.query-keys.ts";
import { stockLotKeys } from "../src/modules/inventory/model/stock-lot.query-keys.ts";
import {
  stockLotDateDependency,
  invalidateStockLotDateViews,
} from "../src/modules/inventory/model/stock-lot-date-dependencies.ts";
import {
  parseStockSerialsParams,
  stockSerialsListParams,
} from "../src/modules/inventory/model/stock-serials-page-state.ts";
import { stockSerialsReturnPath } from "../src/modules/inventory/model/stock-serial-navigation.ts";
const scope = ["tenant", "user", "1"] as const;
const dto = {
  id: "s",
  inventory_item_id: "i",
  number: "000SN-a",
  lot_id: "l",
  lot_number: "000L-a",
  date_source: "LOT" as const,
  manufactured_on: "2024-02-29",
  expires_on: null,
};
test("Serial POST содержит только номер и связь, даты берутся из проекции Lot", () => {
  assert.deepEqual(
    stockSerialCreateToDto({ number: " 000SN-a ", lotId: "l" }),
    { number: " 000SN-a ", lot_id: "l" },
  );
  assert.deepEqual(stockSerialCreateToDto({ number: "000SN-a", lotId: "" }), {
    number: "000SN-a",
    lot_id: null,
  });
  const model = stockSerialFromDto(dto);
  assert.equal(model.number, "000SN-a");
  assert.equal(model.dateSource, "LOT");
  assert.equal(model.manufacturedOn, "2024-02-29");
  assert.equal(
    stockSerialFromDto({
      ...dto,
      date_source: "NONE",
      lot_id: null,
      lot_number: null,
      manufactured_on: null,
    }).dateSource,
    "NONE",
  );
});
test("валидация режимов не требует даты партии REQUIRED при создании", () => {
  assert.equal(allowsStockSerials("SERIAL"), true);
  assert.equal(allowsStockSerials("LOT_AND_SERIAL"), true);
  assert.equal(allowsStockSerials("LOT"), false);
  assert.deepEqual(
    validateStockSerial({ number: "000A", lotId: "" }, "SERIAL"),
    {},
  );
  assert.ok(
    validateStockSerial({ number: "000A", lotId: "" }, "LOT_AND_SERIAL").lotId,
  );
  assert.ok(
    validateStockSerial({ number: "000A", lotId: "l" }, "SERIAL").lotId,
  );
  assert.deepEqual(
    validateStockSerial({ number: "000A", lotId: "l" }, "LOT_AND_SERIAL"),
    {},
  );
  for (const number of ["", "  ", "A\u200b"])
    assert.ok(validateStockSerial({ number, lotId: "" }, "SERIAL").number);
});
test("ключи списка, карточки и кандидатов партий разделены и изолированы по scope", () => {
  const params = { search: "", offset: 0, limit: 50 };
  assert.notDeepEqual(
    stockSerialKeys.list(scope, "i", params),
    stockLotKeys.list(scope, "i", params),
  );
  assert.notDeepEqual(
    stockLotKeys.candidates(scope, "i", ""),
    stockLotKeys.list(scope, "i", params),
  );
  assert.notDeepEqual(
    stockSerialKeys.list(scope, "i", params),
    stockSerialKeys.list(["other", "user", "1"], "i", params),
  );
});
test("редактирование Lot инвалидирует экземпляры и кандидатов только текущего scope", async () => {
  const cache = new QueryClient();
  const list = stockSerialKeys.list(scope, "i", {
    search: "",
    offset: 0,
    limit: 50,
  });
  const detail = stockSerialKeys.detail(scope, "i", "s");
  const other = stockSerialKeys.detail(["other", "user", "1"], "i", "s");
  const candidates = stockLotKeys.candidates(scope, "i", "find");
  for (const key of [list, detail, other])
    await cache.fetchQuery({
      queryKey: key,
      queryFn: () => dto,
      meta: stockLotDateDependency("i", key === detail ? "l" : undefined),
    });
  await cache.fetchQuery({
    queryKey: candidates,
    queryFn: () => ({ pages: [] }),
  });
  await invalidateStockLotDateViews(cache, scope, "i", "l");
  for (const key of [list, detail, candidates])
    assert.equal(cache.getQueryState(key)?.isInvalidated, true);
  assert.equal(cache.getQueryState(other)?.isInvalidated, false);
  cache.clear();
});
test("URL пагинации нормализуется и returnTo не допускает чужие адреса", () => {
  const parsed = parseStockSerialsParams({
    page: "2",
    limit: "20",
    search: " 000SN ",
  });
  assert.deepEqual(stockSerialsListParams(parsed), {
    search: "000SN",
    offset: 20,
    limit: 20,
  });
  assert.equal(
    stockSerialsReturnPath("i", "/inventory/items/i/serials?search=x", true),
    "/inventory/items/i/serials?search=x",
  );
  assert.equal(
    stockSerialsReturnPath("i", "https://external.example", true),
    "/inventory/items/i/serials",
  );
});
