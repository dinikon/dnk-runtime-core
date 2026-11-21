import assert from "node:assert/strict";
import test from "node:test";
import {
  warehouseDefaultStorageFromDto,
  warehouseDefaultStorageToDto,
} from "../src/modules/inventory/api/warehouse-default-storage.mapper.ts";
import {
  DefaultStorageLocationDraft,
  isDefaultStorageCandidate,
} from "../src/modules/inventory/model/default-storage-location-draft.ts";
import { WarehouseDraft } from "../src/modules/inventory/model/warehouse-draft.ts";
import { WarehouseDefaultStorageRequestError } from "../src/modules/inventory/model/warehouse-default-storage.errors.ts";
import { stockLocationKeys } from "../src/modules/inventory/model/stock-location.query-keys.ts";
import { warehouseKeys } from "../src/modules/inventory/model/warehouse.query-keys.ts";
import type { StockLocation } from "../src/modules/inventory/model/stock-location.types.ts";
import type { InventoryScope } from "../src/modules/inventory/model/inventory-scope.types.ts";

const scope: InventoryScope = ["tenant", "user", "1"];
const location: StockLocation = {
  id: "child",
  warehouseId: "warehouse",
  code: "child",
  name: "Child",
  parentLocationId: "inactive-parent",
  locationType: "STORAGE",
  isActive: true,
};

test("default storage payload contains only selected UUID and response preserves inactive warehouse", () => {
  assert.deepEqual(warehouseDefaultStorageToDto({ locationId: "new" }), {
    location_id: "new",
  });
  assert.deepEqual(
    warehouseDefaultStorageFromDto({
      id: "warehouse",
      code: "main",
      name: "Main",
      is_active: false,
      default_storage_location_id: "new",
    }),
    {
      id: "warehouse",
      code: "main",
      name: "Main",
      isActive: false,
      defaultStorageLocationId: "new",
    },
  );
});

test("candidate validation allows active child STORAGE and rejects other warehouses, types and inactive records", () => {
  assert.equal(isDefaultStorageCandidate(location, "warehouse"), true);
  assert.equal(
    isDefaultStorageCandidate(
      { ...location, parentLocationId: null },
      "warehouse",
    ),
    true,
  );
  assert.equal(isDefaultStorageCandidate(location, "other"), false);
  assert.equal(
    isDefaultStorageCandidate({ ...location, isActive: false }, "warehouse"),
    false,
  );
  assert.equal(
    isDefaultStorageCandidate(
      { ...location, locationType: "TRANSIT" },
      "warehouse",
    ),
    false,
  );
  assert.equal(isDefaultStorageCandidate(undefined, "warehouse"), false);
});

test("candidate and mutation keys isolate scope, warehouse and search with fixed server filters", () => {
  const key = stockLocationKeys.defaultStorageCandidates(
    scope,
    "warehouse",
    "search",
  );
  assert.deepEqual(key[7], {
    search: "search",
    limit: 50,
    isActive: true,
    locationType: "STORAGE",
    parentLocationId: null,
  });
  for (const other of [
    stockLocationKeys.defaultStorageCandidates(
      ["tenant-b", "user", "1"],
      "warehouse",
      "search",
    ),
    stockLocationKeys.defaultStorageCandidates(
      ["tenant", "user-b", "1"],
      "warehouse",
      "search",
    ),
    stockLocationKeys.defaultStorageCandidates(
      ["tenant", "user", "2"],
      "warehouse",
      "search",
    ),
    stockLocationKeys.defaultStorageCandidates(scope, "other", "search"),
    stockLocationKeys.defaultStorageCandidates(scope, "warehouse", "next"),
    stockLocationKeys.parents(scope, "warehouse", "search"),
  ])
    assert.notDeepEqual(key, other);
  assert.notDeepEqual(
    warehouseKeys.setDefaultStorage(scope, "warehouse"),
    warehouseKeys.setDefaultStorage(scope, "other"),
  );
  assert.notDeepEqual(
    warehouseKeys.setDefaultStorage(scope, "warehouse"),
    warehouseKeys.setDefaultStorage(["tenant", "user", "2"], "warehouse"),
  );
});

test("selection follows server until edited and preserves the choice during background refresh", () => {
  const draft = new DefaultStorageLocationDraft();
  draft.reset("current");
  draft.receive("external");
  assert.equal(draft.selectedId, "external");
  assert.equal(draft.dirty, false);
  draft.change("chosen");
  draft.receive("new-external");
  assert.equal(draft.selectedId, "chosen");
  assert.equal(draft.dirty, true);
  draft.reset(null);
  assert.equal(draft.selectedId, null);
  assert.equal(draft.dirty, false);
});

test("assignment response cannot acknowledge unsent warehouse edits", () => {
  const initial = { code: "main", name: "Main", isActive: true };
  const draft = new WarehouseDraft();
  draft.receive(initial);
  draft.change({ ...initial, name: "Unsaved", isActive: false });
  const assignment = warehouseDefaultStorageFromDto({
    id: "warehouse",
    code: "main",
    name: "Main",
    is_active: true,
    default_storage_location_id: "new",
  });
  draft.receive(assignment);
  assert.deepEqual(draft.changes, { name: "Unsaved", isActive: false });
  assert.equal(draft.dirty, true);
  const sent = { ...draft.values! };
  draft.acknowledge(sent, { ...assignment, name: "Unsaved", isActive: false });
  assert.equal(draft.dirty, false);
});

test("assignment errors distinguish a rejected choice from an unconfirmed result", () => {
  for (const status of [403, 404, 409, 422]) {
    const error = new WarehouseDefaultStorageRequestError("Rejected", status);
    assert.equal(error.uncertain, false);
    assert.deepEqual(error.fields, {});
  }
  for (const status of [null, 408, 500, 503])
    assert.equal(
      new WarehouseDefaultStorageRequestError("Unconfirmed", status).uncertain,
      true,
    );
});
