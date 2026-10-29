import assert from "node:assert/strict";
import test from "node:test";
import { exampleCompanies } from "../src/modules/example/model/companies-example.constants.ts";
import {
  parseCompaniesExampleParams,
  selectExampleCompanies,
} from "../src/modules/example/model/companies-example.selectors.ts";

test("Companies example filters boolean values and searches names and websites", () => {
  const base = parseCompaniesExampleParams({});
  assert.equal(
    selectExampleCompanies(exampleCompanies, { ...base, icp: "true" }).length,
    9,
  );
  assert.equal(
    selectExampleCompanies(exampleCompanies, { ...base, icp: "false" }).length,
    5,
  );
  assert.deepEqual(
    selectExampleCompanies(exampleCompanies, {
      ...base,
      search: "GOOGLE.COM",
    }).map((item) => item.id),
    ["google"],
  );
  assert.equal(
    selectExampleCompanies(exampleCompanies, { ...base, search: "not present" })
      .length,
    0,
  );
});

test("Companies example sorting is numeric and does not mutate the original rows", () => {
  const params = parseCompaniesExampleParams({
    sort: "arr-desc",
    icp: "false",
  });
  assert.deepEqual(
    selectExampleCompanies(exampleCompanies, params).map((item) => item.id),
    ["google", "nvidia", "microsoft", "linkedin", "notion"],
  );
  assert.equal(exampleCompanies[0]?.id, "anthropic");
  assert.deepEqual(
    parseCompaniesExampleParams({
      search: ["bad"],
      icp: "no",
      sort: "invalid",
    }),
    { search: "", icp: "all", sort: "original" },
  );
});
