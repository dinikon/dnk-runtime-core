import assert from "node:assert/strict";
import test from "node:test";
import {
  SourceDraft,
  sourceChanges,
  sourceValues,
  validateSource,
} from "../src/modules/supplier-sourcing/model/source-draft.ts";
import {
  sourceCreateToDto,
  sourcePatchToDto,
  sourcesParamsToDto,
  sourceFromDto,
} from "../src/modules/supplier-sourcing/api/supplier-source.mapper.ts";
import {
  sourcesParams,
  sourcesQuery,
} from "../src/modules/supplier-sourcing/model/sources-page-state.ts";
import { sourceKeys } from "../src/modules/supplier-sourcing/model/supplier-source.query-keys.ts";
import type { SourceValues } from "../src/modules/supplier-sourcing/model/supplier-source.types.ts";
const initial: SourceValues = {
  supplierModelKey: "crm.company",
  supplierId: "10000000-0000-4000-8000-000000000001",
  name: "Source",
  externalWarehouseCode: "000Code-a",
  fulfillmentModes: ["DROPSHIP"],
  leadTimeSeconds: "0",
  ttlSeconds: "900",
  staleBehavior: "MARK_UNKNOWN",
  missingSkuBehavior: "KEEP_LAST",
  isActive: true,
};
test("создание сохраняет внешний код и передаёт явные настройки, включая нулевой срок", () => {
  const payload = sourceCreateToDto(initial);
  assert.equal(payload.default_lead_time_seconds, 0);
  assert.equal(payload.external_warehouse_code, "000Code-a");
  assert.equal(payload.stock_update_policy.ttl_seconds, 900);
  assert.equal("is_active" in payload, false);
  assert.equal(
    sourceCreateToDto({ ...initial, externalWarehouseCode: " " })
      .external_warehouse_code,
    null,
  );
});
test("PATCH сохраняет false, 0, null и пропуски; политика заменяется целиком", () => {
  assert.deepEqual(
    sourcePatchToDto({
      externalWarehouseCode: null,
      isActive: false,
      defaultLeadTimeSeconds: 0,
    }),
    {
      external_warehouse_code: null,
      is_active: false,
      default_lead_time_seconds: 0,
    },
  );
  assert.deepEqual(sourcePatchToDto({ name: "New" }), { name: "New" });
  const changes = sourceChanges(
    { ...initial, staleBehavior: "BLOCK_AUTOMATIC_SALE" },
    initial,
  );
  assert.deepEqual(sourcePatchToDto(changes), {
    stock_update_policy: {
      ttl_seconds: 900,
      stale_behavior: "BLOCK_AUTOMATIC_SALE",
      missing_sku_behavior: "KEEP_LAST",
    },
  });
});
test("черновик переживает refetch и подтверждение сохраняет более новый ввод", () => {
  const draft = new SourceDraft();
  draft.receive(initial);
  draft.change({
    ...initial,
    name: "Sent",
    fulfillmentModes: ["DROPSHIP", "PURCHASE_TO_WAREHOUSE"],
  });
  const sent = draft.values!;
  draft.change({ ...sent, name: "Newer", ttlSeconds: "1000" });
  draft.receive({ ...initial, name: "refetch" });
  assert.equal(draft.values!.name, "Newer");
  draft.acknowledge(sent, { ...sent, name: "Canonical" });
  assert.equal(draft.values!.name, "Newer");
  assert.equal(draft.values!.ttlSeconds, "1000");
  assert.equal(draft.dirty, true);
  draft.clear();
  assert.equal(draft.values, null);
  assert.equal(draft.dirty, false);
});
test("порядок режимов не создаёт ложные изменения, массивы не разделяются с формой", () => {
  const draft = new SourceDraft();
  const value: SourceValues = {
    ...initial,
    fulfillmentModes: ["DROPSHIP", "PURCHASE_TO_WAREHOUSE"],
  };
  draft.reset(value);
  value.fulfillmentModes.pop();
  assert.equal(draft.values!.fulfillmentModes.length, 2);
  draft.change({
    ...initial,
    fulfillmentModes: ["PURCHASE_TO_WAREHOUSE", "DROPSHIP"],
  });
  assert.equal(draft.dirty, false);
});
test("валидатор допускает нулевой срок, требует положительный TTL и режим", () => {
  assert.deepEqual(validateSource(initial), {});
  for (const ttlSeconds of ["", "0", "-1", "1.5", "true", "86400000000000"])
    assert.ok(validateSource({ ...initial, ttlSeconds }).ttlSeconds);
  assert.ok(
    validateSource({ ...initial, fulfillmentModes: [] }).fulfillmentModes,
  );
  assert.ok(validateSource({ ...initial, supplierId: "" }).supplierId);
  assert.ok(validateSource({ ...initial, name: "  " }).name);
});
test("URL сохраняет серверные фильтры и страницу; false не теряется", () => {
  const params = sourcesParams({
    search: "_%",
    supplier: initial.supplierId,
    supplier_model_key: "crm.company",
    activity: "inactive",
    mode: "DROPSHIP",
    page: "2",
    limit: "50",
  });
  assert.deepEqual(sourcesParams(sourcesQuery(params)), params);
  assert.deepEqual(sourcesParamsToDto(params), {
    offset: 50,
    limit: 50,
    search: "_%",
    supplier_model_key: "crm.company",
    supplier_id: initial.supplierId,
    is_active: false,
    fulfillment_mode: "DROPSHIP",
  });
  assert.equal(sourcesParams({ limit: "999", page: "-1" }).limit, 20);
});
test("ключи кеша разделяют tenant, пользователя, ревизию сессии и фильтры", () => {
  const scope = ["tenant", "user", "1"] as const,
    params = sourcesParams({});
  assert.notDeepEqual(
    sourceKeys.list(scope, params),
    sourceKeys.list(["other", "user", "1"], params),
  );
  assert.notDeepEqual(
    sourceKeys.list(scope, params),
    sourceKeys.list(["tenant", "user", "2"], params),
  );
  assert.notDeepEqual(
    sourceKeys.list(scope, params),
    sourceKeys.list(scope, { ...params, activity: "inactive" }),
  );
});
test("HTTP mapper сохраняет публичное имя компании и все политики", () => {
  const model = sourceFromDto({
    id: "id",
    supplier_model_key: "crm.company",
    supplier_id: initial.supplierId,
    supplier_name: "Company",
    name: "Source",
    external_warehouse_code: "000Code-a",
    fulfillment_modes: ["DROPSHIP"],
    default_lead_time_seconds: 0,
    is_active: false,
    stock_update_policy: {
      ttl_seconds: 900,
      stale_behavior: "BLOCK_AUTOMATIC_SALE",
      missing_sku_behavior: "KEEP_LAST",
    },
  });
  assert.equal(model.supplierName, "Company");
  assert.equal(model.isActive, false);
  assert.deepEqual(sourceValues(model), {
    ...initial,
    isActive: false,
    staleBehavior: "BLOCK_AUTOMATIC_SALE",
  });
});

test("создание контакта передаёт полную пару, PATCH не меняет принадлежность", () => {
  const contact = { ...initial, supplierModelKey: "crm.contact" as const };
  const dto = sourceCreateToDto(contact);
  assert.equal(dto.supplier_model_key, "crm.contact");
  assert.equal(dto.supplier_id, initial.supplierId);
  assert.deepEqual(sourceChanges(contact, initial), {});
  assert.equal(
    "supplier_model_key" in sourcePatchToDto({ name: "New" }),
    false,
  );
});
test("URL и ключи кеша различают типы с одинаковым UUID", () => {
  const company = sourcesParams({
    supplier_model_key: "crm.company",
    supplier: initial.supplierId,
  });
  const contact = sourcesParams({
    supplier_model_key: "crm.contact",
    supplier: initial.supplierId,
  });
  assert.notDeepEqual(
    sourceKeys.list(["tenant", "user", "1"], company),
    sourceKeys.list(["tenant", "user", "1"], contact),
  );
  assert.deepEqual(sourcesParams(sourcesQuery(contact)), contact);
  assert.equal(sourcesParams({ supplier: initial.supplierId }).supplierId, "");
  assert.equal(sourcesParamsToDto(contact).supplier_model_key, "crm.contact");
});
