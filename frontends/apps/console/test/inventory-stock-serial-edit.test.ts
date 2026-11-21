import assert from "node:assert/strict";
import test from "node:test";
import {
  StockSerialDraft,
  stockSerialChanges,
  stockSerialValues,
} from "../src/modules/inventory/model/stock-serial-draft.ts";
import { stockSerialPatchToDto } from "../src/modules/inventory/api/stock-serial.mapper.ts";
import { stockSerialKeys } from "../src/modules/inventory/model/stock-serial.query-keys.ts";
const initial = { number: "000S-a", lotId: "lot-a" };
test("PATCH сохраняет семантику пропуска поля и явного очищения партии", () => {
  assert.deepEqual(stockSerialPatchToDto({ number: "000S-A" }), {
    number: "000S-A",
  });
  assert.deepEqual(stockSerialPatchToDto({ lotId: "" }), { lot_id: null });
  assert.deepEqual(
    stockSerialChanges({ ...initial, lotId: "lot-b" }, initial),
    { lotId: "lot-b" },
  );
  assert.deepEqual(stockSerialChanges(initial, initial), {});
  assert.equal(
    stockSerialValues({
      id: "s",
      inventoryItemId: "i",
      number: "000S-a",
      lotId: null,
      lotNumber: null,
      dateSource: "NONE",
      manufacturedOn: null,
      expiresOn: null,
    }).lotId,
    "",
  );
});
test("фоновое чтение не стирает черновик номера или выбранной партии", () => {
  const draft = new StockSerialDraft();
  draft.receive(initial);
  draft.change({ number: "000NEW", lotId: "lot-b" });
  draft.receive({ number: "server", lotId: "lot-a" });
  assert.deepEqual(draft.values, { number: "000NEW", lotId: "lot-b" });
  assert.equal(draft.dirty, true);
});
test("подтверждение PATCH сохраняет более новый ввод и принимает canonical номер", () => {
  const draft = new StockSerialDraft();
  draft.reset(initial);
  const sent = { number: " 000NEW ", lotId: "lot-b" };
  draft.change(sent);
  draft.change({ ...sent, lotId: "lot-c" });
  draft.acknowledge(sent, { number: "000NEW", lotId: "lot-b" });
  assert.deepEqual(draft.values, { number: "000NEW", lotId: "lot-c" });
  assert.deepEqual(draft.changes, { lotId: "lot-c" });
});
test("проверка неопределённого результата обновляет baseline без потери намерения", () => {
  const draft = new StockSerialDraft();
  draft.reset(initial);
  draft.change({ number: "newer", lotId: "lot-b" });
  draft.rebase({ number: "saved", lotId: "lot-b" });
  assert.deepEqual(draft.values, { number: "newer", lotId: "lot-b" });
  assert.deepEqual(draft.changes, { number: "newer" });
  draft.clear();
  draft.receive(initial);
  assert.equal(draft.dirty, false);
  assert.deepEqual(draft.values, initial);
});
test("ключ изменения изолирован по tenant/session/SKU/Serial", () => {
  const scope = ["tenant", "user", "1"] as const;
  assert.notDeepEqual(
    stockSerialKeys.update(scope, "i", "s"),
    stockSerialKeys.update(scope, "i", "other"),
  );
  assert.notDeepEqual(
    stockSerialKeys.update(scope, "i", "s"),
    stockSerialKeys.update(["tenant", "user", "2"], "i", "s"),
  );
});
