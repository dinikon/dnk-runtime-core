import { computed, ref, type Ref, type ComputedRef } from "vue";
import type {
  ReturnAllocation,
  ReturnPreparation,
  ReturnExecutionValues,
  ReturnExecutionErrors,
  ReturnSource,
} from "./return-posting.types";
import {
  prepareReturnExecution,
  returnExecutionSignature,
  selectedReturnRows,
  splitReturnAllocation,
  rebaseReturnExecution,
  validateReturnExecution,
} from "./return-execution";
interface ReturnExecutionDraft {
  values: Ref<ReturnExecutionValues | null>;
  errors: Ref<ReturnExecutionErrors>;
  dirty: ComputedRef<boolean>;
  initialize: (context: ReturnPreparation) => void;
  reset: () => void;
  change: (key: string, row: ReturnAllocation) => void;
  select: (id: string, selected: boolean) => void;
  split: (key: string) => void;
  remove: (key: string) => void;
  accept: (context: ReturnPreparation) => void;
  updateSources: (sources: Map<string, ReturnSource | null>) => void;
}
export function useReturnExecutionDraft(): ReturnExecutionDraft {
  const values = ref<ReturnExecutionValues | null>(null),
    errors = ref<ReturnExecutionErrors>({ rows: {}, lines: {} }),
    baseline = ref("");
  const dirty = computed(
    () =>
      !!values.value &&
      returnExecutionSignature(values.value) !== baseline.value,
  );
  function reset(): void {
    values.value = null;
    errors.value = { rows: {}, lines: {} };
    baseline.value = "";
  }
  function initialize(context: ReturnPreparation): void {
    values.value = prepareReturnExecution(context, () => crypto.randomUUID());
    baseline.value = returnExecutionSignature(values.value);
  }
  function change(key: string, row: ReturnAllocation): void {
    if (values.value)
      values.value.rows = values.value.rows.map((v) =>
        v.key === key ? { ...row, key: v.key } : v,
      );
  }
  function select(id: string, selected: boolean): void {
    if (values.value)
      values.value.rows = values.value.rows.map((v) =>
        v.documentLineId === id
          ? {
              ...v,
              selected:
                selected &&
                /[1-9]/.test(v.remainingQuantity.split(/[eE]/)[0] ?? ""),
            }
          : v,
      );
  }
  function split(key: string): void {
    if (!values.value || selectedReturnRows(values.value).length >= 500) return;
    const row = values.value.rows.find((v) => v.key === key);
    if (row)
      values.value.rows.push(splitReturnAllocation(row, crypto.randomUUID()));
  }
  function remove(key: string): void {
    if (!values.value) return;
    const row = values.value.rows.find((v) => v.key === key);
    if (!row) return;
    if (
      values.value.rows.filter((v) => v.documentLineId === row.documentLineId)
        .length === 1
    )
      select(row.documentLineId, false);
    else values.value.rows = values.value.rows.filter((v) => v.key !== key);
  }
  function accept(context: ReturnPreparation): void {
    if (values.value) {
      values.value = rebaseReturnExecution(values.value, context);
      errors.value = validateReturnExecution(values.value);
    }
  }
  function updateSources(sources: Map<string, ReturnSource | null>): void {
    if (values.value)
      values.value.rows = values.value.rows.map((row) => {
        if (!row.source) return row;
        const key = JSON.stringify([row.documentLineId, row.source.id]);
        if (!sources.has(key)) return row;
        const source = sources.get(key);
        return {
          ...row,
          source: source ? { ...source } : row.source,
          sourceMissing: !source,
        };
      });
  }
  return {
    values,
    errors,
    dirty,
    reset,
    initialize,
    change,
    select,
    split,
    remove,
    accept,
    updateSources,
  };
}
