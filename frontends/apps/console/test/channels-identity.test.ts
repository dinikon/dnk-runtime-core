import { test } from "node:test";
import assert from "node:assert/strict";
import { mapIdentitySummary } from "../src/modules/channels/api/channels.mapper.ts";
import {
  parseIdentityStatus,
  identityAssessmentLabels,
} from "../src/modules/channels/model/publication-identity.presentation.ts";
import { channelsKeys } from "../src/modules/channels/model/channels.query-keys.ts";

test("identity URL accepts only supported diagnostic states", () => {
  for (const value of [
    undefined,
    null,
    [],
    ["duplicate"],
    "ready",
    "not_required",
  ])
    assert.equal(parseIdentityStatus(value), "");
  for (const value of ["missing", "duplicate", "valid"])
    assert.equal(parseIdentityStatus(value), value);
});
test("public diagnostic mapping retains scope and exact key statistics", () => {
  assert.equal(mapIdentitySummary(null), null);
  const summary = mapIdentitySummary({
    label: "Ключ XML",
    total: 10,
    missing: 3,
    duplicate: 4,
    valid: 3,
    duplicate_groups: 2,
    assessment: "incomplete",
    checked_at: null,
    scope_limitations: ["api_visible_statuses_only"],
    help_title: "Исправление",
    help_steps: ["Шаг"],
    help_url: "https://support.prom.ua/",
    recovery_verified: false,
  });
  assert.equal(summary?.duplicateGroups, 2);
  assert.deepEqual(summary?.scopeLimitations, ["api_visible_statuses_only"]);
  assert.equal(summary?.recoveryVerified, false);
  assert.match(identityAssessmentLabels.incomplete, /не подтверждено/);
  assert.match(identityAssessmentLabels.current, /среди загруженных/);
});
test("identity filter and duplicate key isolate caches along with tenant and connection", () => {
  const filters = {
    offset: 0,
    limit: 20,
    search: "",
    stockStatus: "",
    bindingStatus: "",
    identityStatus: "duplicate",
    identityKey: "00042",
  };
  const base = channelsKeys.publications("t1", "c1", filters);
  for (const other of [
    channelsKeys.publications("t2", "c1", filters),
    channelsKeys.publications("t1", "c2", filters),
    channelsKeys.publications("t1", "c1", { ...filters, identityKey: "42" }),
    channelsKeys.publications("t1", "c1", {
      ...filters,
      identityStatus: "missing",
    }),
  ])
    assert.notDeepEqual(base, other);
});
