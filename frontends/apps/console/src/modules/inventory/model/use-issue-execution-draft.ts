import { computed, ref, type Ref, type ComputedRef } from "vue";
import type {
  IssueAllocation,
  IssuePreparation,
  IssueExecutionValues,
  IssueExecutionErrors,
  IssueSource,
} from "./issue-posting.types";
import {
  prepareIssueExecution,
  issueExecutionSignature,
  selectedIssueRows,
  splitIssueAllocation,
  rebaseIssueExecution,
  validateIssueExecution,
} from "./issue-execution";
interface IssueExecutionDraft {
  values: Ref<IssueExecutionValues | null>;
  errors: Ref<IssueExecutionErrors>;
  dirty: ComputedRef<boolean>;
  initialize: (context: IssuePreparation) => void;
  reset: () => void;
  change: (key: string, row: IssueAllocation) => void;
  select: (id: string, selected: boolean) => void;
  split: (key: string) => void;
  remove: (key: string) => void;
  accept: (context: IssuePreparation) => void;
  updateSources: (sources: Map<string, IssueSource | null>) => void;
}
export function useIssueExecutionDraft(): IssueExecutionDraft {
  const values = ref<IssueExecutionValues | null>(null),
    errors = ref<IssueExecutionErrors>({ rows: {}, lines: {} }),
    baseline = ref("");
  const dirty = computed(
    () =>
      !!values.value &&
      issueExecutionSignature(values.value) !== baseline.value,
  );
  function reset(): void {
    values.value = null;
    errors.value = { rows: {}, lines: {} };
    baseline.value = "";
  }
  function initialize(context: IssuePreparation): void {
    values.value = prepareIssueExecution(context, () => crypto.randomUUID());
    baseline.value = issueExecutionSignature(values.value);
  }
  function change(key: string, row: IssueAllocation): void {
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
    if (!values.value || selectedIssueRows(values.value).length >= 500) return;
    const row = values.value.rows.find((v) => v.key === key);
    if (row)
      values.value.rows.push(splitIssueAllocation(row, crypto.randomUUID()));
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
  function accept(context: IssuePreparation): void {
    if (values.value) {
      values.value = rebaseIssueExecution(values.value, context);
      errors.value = validateIssueExecution(values.value);
    }
  }
  function updateSources(sources: Map<string, IssueSource | null>): void {
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
