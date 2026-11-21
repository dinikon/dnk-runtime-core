import assert from "node:assert/strict";
import test from "node:test";
import { effectScope, ref } from "vue";
import { QueryClient } from "@tanstack/vue-query";
import { stockLotDatesPatchToDto } from "../src/modules/inventory/api/stock-lot.mapper.ts";
import {
  StockLotDatesDraft,
  stockLotDatesValues,
} from "../src/modules/inventory/model/stock-lot-dates-draft.ts";
import { useStockLotDatesDraft } from "../src/modules/inventory/model/use-stock-lot-dates-draft.ts";
import {
  stockLotDateDependency,
  isStockLotDateView,
  invalidateStockLotDateViews,
} from "../src/modules/inventory/model/stock-lot-date-dependencies.ts";
import { stockLotKeys } from "../src/modules/inventory/model/stock-lot.query-keys.ts";
import { validateStockLotDates } from "../src/modules/inventory/model/stock-lot.validation.ts";
import type { StockLotDatesValues } from "../src/modules/inventory/model/stock-lot.types.ts";
const baseline = { manufacturedOn: "2020-01-01", expiresOn: "2030-01-01" };
test("PATCH содержит только изменённые даты, явная очистка даёт null", () => {
  const draft = new StockLotDatesDraft();
  draft.receive(baseline);
  assert.deepEqual(draft.changes, {});
  draft.change({ ...baseline, expiresOn: "" });
  assert.deepEqual(stockLotDatesPatchToDto(draft.changes), {
    expires_on: null,
  });
  draft.change({ ...baseline, manufacturedOn: "0001-01-01" });
  assert.deepEqual(stockLotDatesPatchToDto(draft.changes), {
    manufactured_on: "0001-01-01",
  });
  assert.deepEqual(
    stockLotDatesValues({
      id: "lot",
      inventoryItemId: "item",
      number: "000A",
      manufacturedOn: null,
      expiresOn: null,
    }),
    { manufacturedOn: "", expiresOn: "" },
  );
});
test("REQUIRED допускает неполную карточку, NONE требует очистки срока", () => {
  assert.deepEqual(
    validateStockLotDates({ manufacturedOn: "", expiresOn: "" }, "REQUIRED"),
    {},
  );
  assert.ok(validateStockLotDates(baseline, "NONE").expiresOn);
  assert.deepEqual(
    validateStockLotDates({ ...baseline, expiresOn: "" }, "NONE"),
    {},
  );
  assert.ok(
    validateStockLotDates(
      { manufacturedOn: "2024-03-01", expiresOn: "2024-02-29" },
      "OPTIONAL",
    ).expiresOn,
  );
});
test("refetch не стирает черновик, подтверждение сохраняет более новый ввод", () => {
  const draft = new StockLotDatesDraft();
  draft.receive(baseline);
  const sent = { ...baseline, expiresOn: "2031-01-01" };
  draft.change(sent);
  draft.receive({ manufacturedOn: "2021-01-01", expiresOn: "2040-01-01" });
  assert.deepEqual(draft.values, sent);
  draft.change({
    ...sent,
    manufacturedOn: "2022-01-01",
    expiresOn: "2032-01-01",
  });
  draft.acknowledge(sent, {
    manufacturedOn: "2021-01-01",
    expiresOn: "2031-01-01",
  });
  assert.deepEqual(draft.changes, {
    manufacturedOn: "2022-01-01",
    expiresOn: "2032-01-01",
  });
});
test("неоднозначная запись проверяется чтением без потери локального ввода", () => {
  const draft = new StockLotDatesDraft();
  draft.receive(baseline);
  const submitted = { ...baseline, expiresOn: "2031-01-01" };
  draft.change(submitted);
  draft.rebase(submitted);
  assert.equal(draft.dirty, false);
  draft.change({ ...submitted, manufacturedOn: "2022-01-01" });
  draft.rebase({ ...submitted, manufacturedOn: "2021-01-01" });
  assert.deepEqual(draft.changes, { manufacturedOn: "2022-01-01" });
  draft.clear();
  assert.equal(draft.values, null);
  assert.deepEqual(draft.changes, {});
});
test("watchers не принимают refetch во время записи и очищают форму при смене контекста", () => {
  const scope = effectScope(),
    source = ref<StockLotDatesValues | undefined>({ ...baseline }),
    identity = ref("one"),
    pending = ref(false);
  const draft = scope.run(() =>
    useStockLotDatesDraft(() => source.value, identity, pending),
  )!;
  assert.deepEqual(draft.values.value, baseline);
  pending.value = true;
  source.value = { ...baseline, manufacturedOn: "2021-01-01" };
  assert.deepEqual(draft.values.value, baseline);
  draft.change({ ...baseline, expiresOn: "2032-01-01" });
  pending.value = false;
  assert.equal(draft.values.value?.expiresOn, "2032-01-01");
  identity.value = "two";
  assert.equal(draft.values.value, null);
  source.value = { ...baseline, expiresOn: "2040-01-01" };
  assert.equal(draft.values.value?.expiresOn, "2040-01-01");
  scope.stop();
});
test("изменение дат инвалидирует зарегистрированные серийные проекции и списки только текущего SKU/scope", async () => {
  const cache = new QueryClient(),
    scope = ["tenant", "user", "1"] as const;
  const keys = [
    stockLotKeys.list(scope, "item", { search: "", offset: 0, limit: 50 }),
    ["inventory", ...scope, "serial-view", "item", "serial-a"],
    ["inventory", ...scope, "serial-list", "item"],
    ["inventory", ...scope, "serial-view", "item", "other-lot"],
    ["inventory", ...scope, "serial-view", "other-item", "serial-b"],
    [
      "inventory",
      "other-tenant",
      "user",
      "1",
      "serial-view",
      "item",
      "serial-a",
    ],
    stockLotKeys.detail(scope, "item", "lot"),
  ] as const;
  const meta = [
    undefined,
    stockLotDateDependency("item", "lot"),
    stockLotDateDependency("item"),
    stockLotDateDependency("item", "other-lot"),
    stockLotDateDependency("other-item", "lot"),
    stockLotDateDependency("item", "lot"),
    stockLotDateDependency("item", "lot"),
  ];
  keys.forEach((key, index) => {
    cache.setQueryDefaults(key, { meta: meta[index] });
    cache.setQueryData(key, { value: index });
  });
  await invalidateStockLotDateViews(cache, scope, "item", "lot");
  assert.deepEqual(
    keys.map((key) => cache.getQueryState(key)?.isInvalidated),
    [true, true, true, false, false, false, false],
  );
  assert.equal(
    isStockLotDateView(
      {
        queryKey: ["inventory", ...scope, "serial-view"],
        meta: { inventoryStockLotDates: "invalid" },
      },
      scope,
      "item",
      "lot",
    ),
    false,
  );
  cache.clear();
});
