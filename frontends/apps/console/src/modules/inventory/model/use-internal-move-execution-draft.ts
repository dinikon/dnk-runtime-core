import type { InternalMoveDestination } from "./internal-move-posting.types";
import { computed, ref, type Ref, type ComputedRef } from "vue";
import type {
  InternalMoveAllocation,
  InternalMovePreparation,
  InternalMoveExecutionValues,
  InternalMoveExecutionErrors,
  InternalMoveSource,
} from "./internal-move-posting.types";
import {
  prepareInternalMoveExecution,
  internalMoveExecutionSignature,
  selectedInternalMoveRows,
  splitInternalMoveAllocation,
  rebaseInternalMoveExecution,
  validateInternalMoveExecution,
} from "./internal-move-execution";
interface InternalMoveExecutionDraft {
  values: Ref<InternalMoveExecutionValues | null>;
  errors: Ref<InternalMoveExecutionErrors>;
  dirty: ComputedRef<boolean>;
  initialize: (context: InternalMovePreparation) => void;
  reset: () => void;
  change: (key: string, row: InternalMoveAllocation) => void;
  select: (id: string, selected: boolean) => void;
  split: (key: string) => void;
  remove: (key: string) => void;
  accept: (context: InternalMovePreparation) => void;
  updateDestinations: (
    destinations: Map<string, InternalMoveDestination | null>,
  ) => void;
  updateSources: (sources: Map<string, InternalMoveSource | null>) => void;
}
export function useInternalMoveExecutionDraft(): InternalMoveExecutionDraft {
  const values = ref<InternalMoveExecutionValues | null>(null),
    errors = ref<InternalMoveExecutionErrors>({ rows: {}, lines: {} }),
    baseline = ref("");
  const dirty = computed(
    () =>
      !!values.value &&
      internalMoveExecutionSignature(values.value) !== baseline.value,
  );
  function reset(): void {
    values.value = null;
    errors.value = { rows: {}, lines: {} };
    baseline.value = "";
  }
  function initialize(context: InternalMovePreparation): void {
    values.value = prepareInternalMoveExecution(context, () =>
      crypto.randomUUID(),
    );
    baseline.value = internalMoveExecutionSignature(values.value);
  }
  function change(key: string, row: InternalMoveAllocation): void {
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
    if (!values.value || selectedInternalMoveRows(values.value).length >= 500)
      return;
    const row = values.value.rows.find((v) => v.key === key);
    if (row)
      values.value.rows.push(
        splitInternalMoveAllocation(row, crypto.randomUUID()),
      );
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
  function accept(context: InternalMovePreparation): void {
    if (values.value) {
      values.value = rebaseInternalMoveExecution(values.value, context);
      errors.value = validateInternalMoveExecution(values.value);
    }
  }
  function updateSources(
    sources: Map<string, InternalMoveSource | null>,
  ): void {
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
  function updateDestinations(
    destinations: Map<string, InternalMoveDestination | null>,
  ): void {
    if (values.value)
      values.value.rows = values.value.rows.map((row) => {
        if (!row.destination || !destinations.has(row.destination.id))
          return row;
        const destination = destinations.get(row.destination.id);
        return {
          ...row,
          destination: destination ? { ...destination } : row.destination,
          destinationMissing: !destination,
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
    updateDestinations,
  };
}
