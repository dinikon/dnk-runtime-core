import { computed } from "vue";
import {
  useRoute,
  useRouter,
  type LocationQuery,
  type LocationQueryRaw,
} from "vue-router";

import type {
  RuntimeFieldDescription,
  RuntimeFilter,
  RuntimeFilterCondition,
  RuntimeSort,
} from "@/shared/runtime-object";

export const RUNTIME_OBJECT_DEFAULT_PAGE_SIZE = 50;
export const RUNTIME_OBJECT_PAGE_SIZES = [10, 25, 50, 100] as const;

type RuntimeObjectPageSize = (typeof RUNTIME_OBJECT_PAGE_SIZES)[number];

interface RuntimeObjectQueryState {
  filter: RuntimeFilter | null;
  sort: RuntimeSort[];
  limit: RuntimeObjectPageSize;
  offset: number;
  isValid: boolean;
}

interface RuntimeObjectQueryPatch {
  filter?: RuntimeFilter | null;
  sort?: RuntimeSort[];
  limit?: number;
  offset?: number;
}

const runtimeQueryKeys = ["filter", "sort", "limit", "offset"] as const;

export function useRuntimeObjectQueryState() {
  const route = useRoute();
  const router = useRouter();

  const state = computed(() => parseRuntimeObjectQuery(route.query));

  const filter = computed(() => state.value.filter);
  const sort = computed(() => state.value.sort);
  const limit = computed(() => state.value.limit);
  const offset = computed(() => state.value.offset);
  const hasInvalidQuery = computed(() => !state.value.isValid);

  function pushState(patch: RuntimeObjectQueryPatch) {
    return navigate("push", route.query, patch);
  }

  function replaceState(patch: RuntimeObjectQueryPatch = {}) {
    return navigate("replace", route.query, patch);
  }

  function navigate(
    mode: "push" | "replace",
    currentQuery: LocationQuery,
    patch: RuntimeObjectQueryPatch,
  ) {
    const nextQuery = buildRuntimeObjectQuery(currentQuery, {
      filter: filter.value,
      sort: sort.value,
      limit: limit.value,
      offset: offset.value,
      ...patch,
    });

    if (hasSameRuntimeQuery(currentQuery, nextQuery)) {
      return Promise.resolve();
    }

    return router[mode]({
      path: route.path,
      query: nextQuery,
      hash: route.hash,
    });
  }

  return {
    filter,
    sort,
    limit,
    offset,
    hasInvalidQuery,
    pushState,
    replaceState,
  };
}

export function sanitizeRuntimeFilterForFields(
  filter: RuntimeFilter | null,
  fields: RuntimeFieldDescription[],
): RuntimeFilter | null {
  if (!filter) {
    return null;
  }

  const filterableFields = new Map(
    fields
      .filter((field) => field.filter.enabled)
      .map((field) => [field.field_name, field]),
  );

  return sanitizeFilterNode(filter, filterableFields);
}

export function sanitizeRuntimeSortForFields(
  sort: RuntimeSort[],
  fields: RuntimeFieldDescription[],
): RuntimeSort[] {
  const sortableFields = new Set(
    fields
      .filter((field) => field.sort.enabled)
      .map((field) => field.field_name),
  );
  const seen = new Set<string>();

  return sort.filter((item) => {
    if (!sortableFields.has(item.field) || seen.has(item.field)) {
      return false;
    }

    seen.add(item.field);
    return true;
  });
}

export function areRuntimeFiltersEqual(
  left: RuntimeFilter | null,
  right: RuntimeFilter | null,
): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

export function areRuntimeSortsEqual(
  left: RuntimeSort[],
  right: RuntimeSort[],
): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

function parseRuntimeObjectQuery(
  query: LocationQuery,
): RuntimeObjectQueryState {
  const parsedFilter = parseFilterQueryValue(firstQueryValue(query.filter));
  const parsedSort = parseSortQueryValue(firstQueryValue(query.sort));
  const parsedLimit = parseLimitQueryValue(firstQueryValue(query.limit));
  const parsedOffset = parseOffsetQueryValue(firstQueryValue(query.offset));

  return {
    filter: parsedFilter.value,
    sort: parsedSort.value,
    limit: parsedLimit.value,
    offset: parsedOffset.value,
    isValid:
      parsedFilter.isValid &&
      parsedSort.isValid &&
      parsedLimit.isValid &&
      parsedOffset.isValid,
  };
}

function parseFilterQueryValue(value: string | null): {
  value: RuntimeFilter | null;
  isValid: boolean;
} {
  if (value === null) {
    return { value: null, isValid: true };
  }

  try {
    const decoded = decodeBase64Url(value);
    const parsed = JSON.parse(decoded) as unknown;
    const filter = parseRuntimeFilter(parsed);

    return { value: filter, isValid: filter !== null };
  } catch {
    return { value: null, isValid: false };
  }
}

function parseSortQueryValue(value: string | null): {
  value: RuntimeSort[];
  isValid: boolean;
} {
  if (value === null) {
    return { value: [], isValid: true };
  }

  const sort: RuntimeSort[] = [];
  const seen = new Set<string>();
  let isValid = true;

  for (const item of value.split(",")) {
    const [field, direction, ...rest] = item.split(":");

    if (
      rest.length > 0 ||
      !field ||
      (direction !== "asc" && direction !== "desc")
    ) {
      isValid = false;
      continue;
    }

    if (seen.has(field)) {
      isValid = false;
      continue;
    }

    seen.add(field);
    sort.push({ field, direction });
  }

  return { value: sort, isValid };
}

function parseLimitQueryValue(value: string | null): {
  value: RuntimeObjectPageSize;
  isValid: boolean;
} {
  if (value === null) {
    return { value: RUNTIME_OBJECT_DEFAULT_PAGE_SIZE, isValid: true };
  }

  const parsed = parsePositiveInteger(value);
  const isPageSize = RUNTIME_OBJECT_PAGE_SIZES.some((size) => size === parsed);

  return {
    value: isPageSize
      ? (parsed as RuntimeObjectPageSize)
      : RUNTIME_OBJECT_DEFAULT_PAGE_SIZE,
    isValid: isPageSize,
  };
}

function parseOffsetQueryValue(value: string | null): {
  value: number;
  isValid: boolean;
} {
  if (value === null) {
    return { value: 0, isValid: true };
  }

  const parsed = parsePositiveInteger(value);
  return {
    value: parsed === null ? 0 : parsed,
    isValid: parsed !== null,
  };
}

function buildRuntimeObjectQuery(
  currentQuery: LocationQuery,
  patch: Required<RuntimeObjectQueryPatch>,
): LocationQueryRaw {
  const query: LocationQueryRaw = { ...currentQuery };

  if (patch.filter) {
    query.filter = encodeBase64Url(JSON.stringify(patch.filter));
  } else {
    delete query.filter;
  }

  if (patch.sort.length > 0) {
    query.sort = patch.sort
      .map((item) => `${item.field}:${item.direction}`)
      .join(",");
  } else {
    delete query.sort;
  }

  if (isRuntimeObjectPageSize(patch.limit)) {
    if (patch.limit === RUNTIME_OBJECT_DEFAULT_PAGE_SIZE) {
      delete query.limit;
    } else {
      query.limit = String(patch.limit);
    }
  } else {
    delete query.limit;
  }

  const offset = Math.max(0, Math.floor(patch.offset));
  if (offset === 0) {
    delete query.offset;
  } else {
    query.offset = String(offset);
  }

  return query;
}

function hasSameRuntimeQuery(
  currentQuery: LocationQuery,
  nextQuery: LocationQueryRaw,
): boolean {
  return runtimeQueryKeys.every(
    (key) =>
      firstQueryValue(currentQuery[key]) === firstQueryValue(nextQuery[key]),
  );
}

function sanitizeFilterNode(
  filter: RuntimeFilter,
  fields: Map<string, RuntimeFieldDescription>,
): RuntimeFilter | null {
  if ("field" in filter) {
    return sanitizeFilterCondition(filter, fields);
  }

  if ("and" in filter) {
    return sanitizeFilterGroup("and", filter.and, fields);
  }

  return sanitizeFilterGroup("or", filter.or, fields);
}

function sanitizeFilterCondition(
  condition: RuntimeFilterCondition,
  fields: Map<string, RuntimeFieldDescription>,
): RuntimeFilterCondition | null {
  const field = fields.get(condition.field);
  if (!field || !field.filter.operators.includes(condition.op)) {
    return null;
  }

  return condition;
}

function sanitizeFilterGroup(
  logic: "and" | "or",
  items: RuntimeFilter[],
  fields: Map<string, RuntimeFieldDescription>,
): RuntimeFilter | null {
  const sanitizedItems = items
    .map((item) => sanitizeFilterNode(item, fields))
    .filter((item): item is RuntimeFilter => item !== null);

  if (sanitizedItems.length === 0) {
    return null;
  }

  if (sanitizedItems.length === 1) {
    return sanitizedItems[0];
  }

  return logic === "and" ? { and: sanitizedItems } : { or: sanitizedItems };
}

function parseRuntimeFilter(value: unknown): RuntimeFilter | null {
  if (!isRecord(value)) {
    return null;
  }

  if (
    typeof value.field === "string" &&
    typeof value.op === "string" &&
    Object.prototype.hasOwnProperty.call(value, "value")
  ) {
    return {
      field: value.field,
      op: value.op,
      value: value.value,
    };
  }

  if (Array.isArray(value.and)) {
    const items = value.and.map((item) => parseRuntimeFilter(item));

    if (items.some((item) => item === null)) {
      return null;
    }

    return { and: items as RuntimeFilter[] };
  }

  if (Array.isArray(value.or)) {
    const items = value.or.map((item) => parseRuntimeFilter(item));

    if (items.some((item) => item === null)) {
      return null;
    }

    return { or: items as RuntimeFilter[] };
  }

  return null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function firstQueryValue(
  value: LocationQuery[string] | LocationQueryRaw[string] | undefined,
): string | null {
  if (Array.isArray(value)) {
    return typeof value[0] === "string" && value[0] ? value[0] : null;
  }

  return typeof value === "string" && value ? value : null;
}

function parsePositiveInteger(value: string): number | null {
  if (!/^\d+$/.test(value)) {
    return null;
  }

  const parsed = Number(value);
  return Number.isSafeInteger(parsed) ? parsed : null;
}

function isRuntimeObjectPageSize(
  value: number,
): value is RuntimeObjectPageSize {
  return RUNTIME_OBJECT_PAGE_SIZES.some((size) => size === value);
}

function encodeBase64Url(value: string): string {
  const bytes = new TextEncoder().encode(value);
  let binary = "";

  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }

  return btoa(binary)
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replace(/=+$/, "");
}

function decodeBase64Url(value: string): string {
  const normalized = value.replaceAll("-", "+").replaceAll("_", "/");
  const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
  const binary = atob(padded);
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));

  return new TextDecoder().decode(bytes);
}
