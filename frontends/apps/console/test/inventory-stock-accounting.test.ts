import assert from "node:assert/strict";
import test from "node:test";
import {
  readStockAccountingQuery,
  changeStockFilters,
} from "../src/modules/inventory/model/stock-accounting-state.ts";
import {
  stockReadLocation,
  accountingTarget,
} from "../src/modules/inventory/model/stock-accounting-navigation.ts";
import { stockAccountingKeys } from "../src/modules/inventory/model/stock-accounting.query-keys.ts";
import {
  listStockPositionsResultFromDto,
  getStockPositionResultFromDto,
} from "../src/modules/inventory/api/stock-accounting.mapper.ts";
const item = "00000000-0000-4000-8000-000000000001",
  warehouse = "00000000-0000-4000-8000-000000000002";
test("accounting URL preserves exact IDs, pagination and zero selector and rejects malformed context", () => {
  const parsed = readStockAccountingQuery(
    {
      inventory_item_id: item,
      warehouse_id: warehouse,
      include_zero: "true",
      offset: "40",
    },
    "positions",
  );
  assert.equal(parsed.error, "");
  assert.equal(parsed.params.offset, 40);
  assert.equal(parsed.params.filters.includeZero, true);
  assert.deepEqual(
    stockReadLocation("positions", parsed.params.filters).query,
    { warehouse_id: warehouse, inventory_item_id: item, include_zero: "true" },
  );
  assert.match(
    readStockAccountingQuery({ lot_id: "not-an-id" }, "positions").error,
    /Некорректная/,
  );
  assert.equal(
    readStockAccountingQuery({ offset: "NaN" }, "positions").params.offset,
    0,
  );
  assert.equal(
    readStockAccountingQuery(
      { include_zero: "true", execution_id: item },
      "movements",
    ).params.filters.includeZero,
    undefined,
  );
  assert.match(
    readStockAccountingQuery(
      {
        posted_from: "2026-02-01T00:00:00Z",
        posted_to: "2026-01-01T00:00:00Z",
      },
      "movements",
    ).error,
    /Начало/,
  );
});
test("changing parent filters clears only dependent selections", () => {
  const original = {
    warehouseId: warehouse,
    locationId: "loc",
    inventoryItemId: item,
    lotId: "lot",
    serialId: "serial",
    ownerId: "owner",
  };
  assert.deepEqual(changeStockFilters(original, { warehouseId: "other" }), {
    warehouseId: "other",
    inventoryItemId: item,
    lotId: "lot",
    serialId: "serial",
    ownerId: "owner",
  });
  const changed = changeStockFilters(original, { inventoryItemId: undefined });
  assert.equal(changed.lotId, undefined);
  assert.equal(changed.serialId, undefined);
  assert.equal(changed.ownerId, "owner");
  assert.equal(
    changeStockFilters(original, { lotId: "other" }).serialId,
    undefined,
  );
  assert.equal(original.serialId, "serial");
});
test("physical cache keys isolate tenant/user/session, snapshot filters and preserve precision through mapping", () => {
  const params = { filters: { inventoryItemId: item }, offset: 0, limit: 20 };
  const key = stockAccountingKeys.listStockPositions(
    ["tenant", "user", "1"],
    params,
  );
  params.filters.inventoryItemId = "changed";
  assert.equal(key[6].filters.inventoryItemId, item);
  assert.notDeepEqual(
    key,
    stockAccountingKeys.listStockPositions(["other", "user", "1"], params),
  );
  assert.notDeepEqual(
    key,
    stockAccountingKeys.listStockPositions(["tenant", "other", "1"], params),
  );
  const exact = "1234567890.1234567890123456789";
  const row = {
    id: item,
    inventory_item_id: item,
    sku: "000Sku",
    warehouse_id: warehouse,
    warehouse_code: "MAIN",
    warehouse_name: "Main",
    warehouse_is_active: false,
    location_id: item,
    location_code: "A1",
    location_name: "A1",
    location_is_active: true,
    owner_id: item,
    owner_name: null,
    lot_id: null,
    lot_number: null,
    serial_id: null,
    serial_number: null,
    stock_status: "SELLABLE",
    base_uom: "KG",
    manufactured_on: null,
    expires_on: null,
    on_hand_qty: exact,
    version: 3,
  };
  const result = listStockPositionsResultFromDto({
    items: [row],
    total: 1,
    offset: 0,
    limit: 20,
  });
  assert.equal(result.items[0].onHandQty, exact);
  assert.equal(result.items[0].lotId, null);
  assert.equal(result.items[0].warehouseIsActive, false);
  assert.equal(
    getStockPositionResultFromDto({ ...row, ledger_quantity: exact })
      .ledgerQuantity,
    exact,
  );
});
test("trace navigation addresses stable identities instead of mutable labels", () => {
  assert.deepEqual(accountingTarget({ kind: "lot", id: "lot", itemId: item }), {
    name: "inventory-stock-lot",
    params: { lotId: "lot", inventoryItemId: item },
  });
  assert.deepEqual(accountingTarget({ kind: "position", id: item }), {
    name: "inventory-stock-position",
    params: { positionId: item },
  });
});

test("traceability columns are hidden by default and restore independently from the URL", async () => {
  const { readTrackingColumns, trackingColumnsQuery } =
    await import("../src/modules/inventory/model/stock-accounting-state.ts");
  assert.deepEqual(readTrackingColumns(undefined), {
    lot: false,
    serial: false,
  });
  assert.deepEqual(readTrackingColumns("lot"), { lot: true, serial: false });
  assert.deepEqual(readTrackingColumns("serial"), { lot: false, serial: true });
  assert.equal(trackingColumnsQuery({ lot: true, serial: true }), "lot,serial");
  assert.equal(trackingColumnsQuery({ lot: false, serial: false }), undefined);
  assert.deepEqual(readTrackingColumns("unknown"), {
    lot: false,
    serial: false,
  });
});

test("summary cache keys include grouping choices without mixing them with individual positions", () => {
  const params = {
    filters: { inventoryItemId: item },
    offset: 0,
    limit: 20,
    groupByLot: false,
    groupBySerial: false,
  };
  const summary = stockAccountingKeys.listStockBalances(
    ["tenant", "user", "1"],
    params,
  );
  const lots = stockAccountingKeys.listStockBalances(["tenant", "user", "1"], {
    ...params,
    groupByLot: true,
  });
  const serials = stockAccountingKeys.listStockBalances(
    ["tenant", "user", "1"],
    { ...params, groupBySerial: true },
  );
  assert.notDeepEqual(summary, lots);
  assert.notDeepEqual(summary, serials);
  assert.notDeepEqual(
    summary,
    stockAccountingKeys.listStockPositions(["tenant", "user", "1"], params),
  );
  params.groupByLot = true;
  assert.equal(summary[6].groupByLot, false);
});

test("period ordering compares instants across timezone offsets without rounding quantities", () => {
  const result = readStockAccountingQuery(
    {
      posted_from: "2026-01-01T10:00:00+02:00",
      posted_to: "2026-01-01T09:00:00Z",
    },
    "movements",
  );
  assert.equal(result.error, "");
  assert.equal(result.params.filters.postedFrom, "2026-01-01T10:00:00+02:00");
});

test("pagination recovers after grouping or filters remove the requested page", async () => {
  const { stockAccountingPageOffset } =
    await import("../src/modules/inventory/model/stock-accounting-state.ts");
  assert.equal(stockAccountingPageOffset(80, 0), 0);
  assert.equal(stockAccountingPageOffset(80, 21), 20);
  assert.equal(stockAccountingPageOffset(20, 60), 20);
  assert.equal(stockAccountingPageOffset(45, 60), 45);
});
