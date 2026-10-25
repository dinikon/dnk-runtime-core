import { test } from "node:test";
import assert from "node:assert/strict";
import {
  cloneImportConfiguration,
  acknowledgeImportConfiguration,
  importConfigurationEquals,
  importMappingPreview,
} from "../src/modules/catalog/model/import.draft.ts";
import {
  importDetailsFromDto,
  importConfigurationToDto,
} from "../src/modules/catalog/api/import.mapper.ts";
import {
  importIsActive,
  importIsFinished,
} from "../src/modules/catalog/model/import.constants.ts";
import type { ImportConfiguration } from "../src/modules/catalog/model/import.types.ts";
import type { GetImportResponse } from "../src/modules/catalog/api/import.dto.ts";

const configuration: ImportConfiguration = {
  mappings: [
    { target: "sku", source: "c:0", constant: null, locale: null },
    { target: "title", source: "c:1", constant: null, locale: "uk" },
    { target: "regular_price", source: "c:2", constant: null, locale: null },
    { target: "virtual", source: "c:3", constant: null, locale: null },
  ],
  mode: "create",
  clearEmpty: false,
  defaultLocale: "uk",
  timezone: "Europe/Kyiv",
  encoding: "utf-8-sig",
  delimiter: ",",
  recordPath: null,
};

test("mapping keeps duplicate columns by ID and zero/false/empty meanings", () => {
  const result = importMappingPreview(configuration, {
    "c:0": ["SKU"],
    "c:1": ["Назва"],
    "c:2": ["0"],
    "c:3": ["false"],
  });
  assert.deepEqual(result, {
    sku: ["SKU"],
    "title (uk)": ["Назва"],
    regular_price: ["0"],
    virtual: ["false"],
  });
  assert.deepEqual(importMappingPreview(configuration, { "c:2": [""] }), {});
  assert.deepEqual(
    importMappingPreview(
      { ...configuration, clearEmpty: true },
      { "c:2": [""] },
    ),
    { regular_price: [""] },
  );
});

test("editing a draft never changes the cached configuration", () => {
  const draft = cloneImportConfiguration(configuration);
  draft.mappings[0]!.source = "c:7";
  assert.equal(configuration.mappings[0]!.source, "c:0");
  assert.equal(importConfigurationEquals(draft, configuration), false);
  assert.equal(
    importConfigurationEquals(
      cloneImportConfiguration(configuration),
      configuration,
    ),
    true,
  );
});

test("API mapping preserves source IDs, constants, UTC dates and decimal strings", () => {
  const dto: GetImportResponse = {
    run: {
      id: "one",
      source_name: "products.csv",
      status: "mapping",
      version: 2,
      generation: 1,
      can_resume: true,
      total: 19,
      processed: 0,
      created: 0,
      updated: 0,
      skipped: 0,
      errors: 0,
      warnings: 0,
      created_at: "2026-10-25T12:00:00Z",
      finished_at: null,
      error: null,
    },
    configuration: importConfigurationToDto(configuration),
    analysis: {
      format: "csv",
      encoding: "utf-8-sig",
      delimiter: ",",
      record_path: null,
      candidates: [],
      fields: [{ id: "c:2", label: "Ціна" }],
      samples: [{ number: 1, values: { "c:2": ["507,7"] } }],
      mapped_samples: [],
      warnings: [],
    },
  };
  const result = importDetailsFromDto(dto);
  assert.equal(result.run.createdAt.toISOString(), "2026-10-25T12:00:00.000Z");
  assert.equal(result.run.finishedAt, null);
  assert.equal(result.run.generation, 1);
  assert.equal(result.run.canResume, true);
  assert.equal(result.analysis.samples[0]!.values["c:2"]![0], "507,7");
  assert.deepEqual(
    importConfigurationToDto(result.configuration),
    dto.configuration,
  );
  result.analysis.samples[0]!.values["c:2"]![0] = "changed";
  assert.equal(dto.analysis.samples[0]!.values["c:2"]![0], "507,7");
});

test("polling stops for mapping and terminal states", () => {
  for (const status of [
    "preparing",
    "queued",
    "running",
    "cancelling",
  ] as const)
    assert.equal(importIsActive(status), true);
  for (const status of [
    "mapping",
    "completed",
    "failed",
    "cancelled",
    "completed_with_errors",
    "expired",
  ] as const)
    assert.equal(importIsActive(status), false);
  assert.equal(importIsFinished("mapping"), false);
  assert.equal(importIsFinished("completed_with_errors"), true);
});

test("preview acknowledgement preserves edits made after submitting a snapshot", () => {
  const previous = cloneImportConfiguration(configuration);
  const submitted = {
    ...cloneImportConfiguration(previous),
    defaultLocale: "ru",
  };
  const current = { ...cloneImportConfiguration(submitted), clearEmpty: true };
  const confirmed = cloneImportConfiguration(submitted);
  assert.equal(
    acknowledgeImportConfiguration(current, previous, submitted, confirmed)
      .clearEmpty,
    true,
  );
  assert.deepEqual(
    acknowledgeImportConfiguration(submitted, previous, submitted, confirmed),
    confirmed,
  );
});
