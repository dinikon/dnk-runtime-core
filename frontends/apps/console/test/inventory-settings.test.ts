import assert from "node:assert/strict";
import test from "node:test";
import { effectScope, ref, nextTick } from "vue";
import {
  inventoryItemDetailsFromDto,
  inventoryItemSettingsToDto,
  inventoryUomsFromDto,
} from "../src/modules/inventory/api/inventory-item-settings.mapper.ts";
import { InventorySettingsDraft } from "../src/modules/inventory/model/inventory-item-settings-draft.ts";
import { useInventoryItemSettingsDraft } from "../src/modules/inventory/model/use-inventory-item-settings-draft.ts";
import { validateInventorySettings } from "../src/modules/inventory/model/inventory-item-settings.validation.ts";
import {
  inventoryItemReturnPath,
  inventoryItemEditLocation,
} from "../src/modules/inventory/model/inventory-item-navigation.ts";
import type { InventoryItemSettings } from "../src/modules/inventory/model/inventory-item-settings.types.ts";

const defaults: InventoryItemSettings = {
  baseUom: "PCS",
  quantityStep: "1",
  trackingMode: "NONE",
  expirationMode: "NONE",
};
const uoms = [
  { code: "PCS", dimension: "COUNT" },
  { code: "KG", dimension: "MASS" },
] as const;

test("detail mapping and settings PATCH retain exact decimals and omit unrelated fields", () => {
  const value = inventoryItemDetailsFromDto({
    id: "item",
    sku: "sku",
    base_uom: "KG",
    quantity_rules: { step: "1.234567890123456789E-40" },
    tracking_mode: "LOT",
    expiration_mode: "REQUIRED",
    barcodes: [{ id: "barcode-id", barcode: "000a" }],
  });
  const payload = inventoryItemSettingsToDto(value);
  assert.deepEqual(payload, {
    base_uom: "KG",
    quantity_rules: { step: "1.234567890123456789E-40" },
    tracking_mode: "LOT",
    expiration_mode: "REQUIRED",
  });
  assert.deepEqual(value.barcodes, [{ id: "barcode-id", barcode: "000a" }]);
  assert.deepEqual(inventoryUomsFromDto({ items: [...uoms] }), uoms);
});

test("validation accepts exact positive decimals, including API powers without floating point", () => {
  for (const quantityStep of [
    "1",
    "1E-1000",
    "+.1",
    "1.",
    "0.0000000000000000000000000000000001",
    "123456789012345678901234567890.12345678901234567890",
  ]) {
    assert.deepEqual(
      validateInventorySettings({ ...defaults, quantityStep }, uoms),
      {},
    );
  }
  for (const quantityStep of [
    "",
    "0",
    "0E999",
    "-1",
    "NaN",
    "Infinity",
    "1,5",
    "abc",
    "1e",
    "1e1.5",
  ]) {
    assert.ok(
      validateInventorySettings({ ...defaults, quantityStep }, uoms)
        .quantityStep,
      quantityStep,
    );
  }
});

test("coupled tracking, unit, step and expiration rules match Domain", () => {
  for (const trackingMode of ["SERIAL", "LOT_AND_SERIAL"] as const) {
    for (const quantityStep of ["1", "1.00", "10e-1", ".01E2", "0.00100e3"]) {
      assert.deepEqual(
        validateInventorySettings(
          {
            ...defaults,
            trackingMode,
            quantityStep,
            expirationMode: "REQUIRED",
          },
          uoms,
        ),
        {},
      );
    }
    const invalid = validateInventorySettings(
      {
        ...defaults,
        trackingMode,
        baseUom: "KG",
        quantityStep: "1.00000000000000000000000001",
      },
      uoms,
    );
    assert.ok(invalid.baseUom);
    assert.ok(invalid.quantityStep);
  }
  assert.ok(
    validateInventorySettings({ ...defaults, expirationMode: "REQUIRED" }, uoms)
      .expirationMode,
  );
  assert.deepEqual(
    validateInventorySettings(
      { ...defaults, expirationMode: "OPTIONAL" },
      uoms,
    ),
    {},
  );
  assert.ok(
    validateInventorySettings({ ...defaults, baseUom: "UNKNOWN" }, uoms)
      .baseUom,
  );
});

test("draft ignores background refetch and acknowledges only submitted fields", () => {
  const draft = new InventorySettingsDraft();
  draft.receive(defaults);
  const sent = { ...defaults, baseUom: "KG", quantityStep: "0.001" };
  draft.change(sent);
  draft.receive({ ...defaults, quantityStep: "2" });
  assert.deepEqual(draft.values, sent);
  // A newer edit can even revert a field to its initial value during the request.
  draft.change({ ...sent, quantityStep: "1" });
  draft.acknowledge(sent, { ...sent, quantityStep: "0.0010" });
  assert.equal(draft.values?.quantityStep, "1");
  assert.equal(draft.dirty, true);
  draft.reset({ ...sent, quantityStep: "0.0010" });
  assert.equal(draft.dirty, false);
  draft.clear();
  assert.equal(draft.values, null);
});

test("draft context reset clears input and blocks refetch until request acknowledgement", async () => {
  const effects = effectScope(),
    identity = ref("tenant-a:item"),
    pending = ref(false);
  const data = ref<InventoryItemSettings | undefined>(defaults);
  const draft = effects.run(() =>
    useInventoryItemSettingsDraft(() => data.value, identity, pending),
  )!;
  try {
    const sent = { ...defaults, quantityStep: "2" };
    draft.change(sent);
    pending.value = true;
    draft.change(defaults);
    data.value = sent;
    assert.deepEqual(draft.values.value, defaults);
    draft.acknowledge(sent, sent);
    pending.value = false;
    assert.deepEqual(draft.values.value, defaults);
    assert.equal(draft.dirty.value, true);
    identity.value = "tenant-b:item";
    data.value = undefined;
    await nextTick();
    assert.equal(draft.values.value, null);
    data.value = { ...defaults, quantityStep: "3" };
    await nextTick();
    assert.equal(draft.values.value?.quantityStep, "3");
  } finally {
    effects.stop();
  }
});

test("editor navigation preserves origin parameters and rejects external destinations", () => {
  const origin = "/catalog/items/root?locale=ru&variant=child&tab=variants#sku";
  assert.deepEqual(inventoryItemEditLocation("inventory-id", origin), {
    name: "inventory-item-edit",
    params: { inventoryItemId: "inventory-id" },
    query: { returnTo: origin },
  });
  assert.equal(inventoryItemReturnPath(origin), origin);
  assert.equal(
    inventoryItemReturnPath("/inventory/items?search=sku&page=2&limit=20"),
    "/inventory/items?search=sku&page=2&limit=20",
  );
  for (const origin of [
    "https://outside.test",
    "//outside.test",
    "/inventory/items\\evil",
    undefined,
  ])
    assert.equal(inventoryItemReturnPath(origin), "/inventory/items");
});
