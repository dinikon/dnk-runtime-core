import { computed, ref, type ComputedRef, type Ref } from "vue";
import {
  prepareIntake,
  intakeSignature,
  duplicateIntakeRow,
  selectIntakeLine,
  selectedIntakeRows,
  rebaseIntake,
  validateIntake,
} from "./receipt-intake";
import type {
  IntakeRow,
  ReceiptIntakeValues,
  ReceiptIntakeErrors,
  ReceiptPreparation,
} from "./receipt-posting.types";

interface ReceiptIntakeDraft {
  values: Ref<ReceiptIntakeValues | null>;
  errors: Ref<ReceiptIntakeErrors>;
  dirty: ComputedRef<boolean>;
  reset: () => void;
  initialize: (context: ReceiptPreparation) => void;
  change: (key: string, row: IntakeRow) => void;
  remove: (key: string) => void;
  split: (key: string) => void;
  select: (id: string, selected: boolean) => void;
  fill: (context: ReceiptPreparation, id: string) => void;
  accept: (context: ReceiptPreparation) => void;
}
export function useReceiptIntakeDraft(): ReceiptIntakeDraft {
  const values = ref<ReceiptIntakeValues | null>(null);
  const errors = ref<ReceiptIntakeErrors>({ rows: {} });
  const baseline = ref("");
  const dirty = computed(
    () => !!values.value && intakeSignature(values.value) !== baseline.value,
  );
  function reset(): void {
    values.value = null;
    errors.value = { rows: {} };
    baseline.value = "";
  }
  function initialize(context: ReceiptPreparation): void {
    values.value = prepareIntake(context, () => crypto.randomUUID());
    baseline.value = intakeSignature(values.value);
  }
  function change(key: string, row: IntakeRow): void {
    if (values.value)
      values.value.rows = values.value.rows.map((value) =>
        value.key === key ? { ...row, key: value.key } : value,
      );
  }
  function remove(key: string): void {
    if (!values.value) return;
    const row = values.value.rows.find((value) => value.key === key);
    if (!row) return;
    if (
      values.value.rows.filter(
        (value) => value.documentLineId === row.documentLineId,
      ).length === 1
    ) {
      values.value = selectIntakeLine(values.value, row.documentLineId, false);
    } else
      values.value.rows = values.value.rows.filter(
        (value) => value.key !== key,
      );
  }
  function split(key: string): void {
    if (!values.value || selectedIntakeRows(values.value).length >= 500) return;
    const row = values.value.rows.find((value) => value.key === key);
    if (row)
      values.value.rows.push(duplicateIntakeRow(row, crypto.randomUUID()));
  }
  function select(id: string, selected: boolean): void {
    if (values.value)
      values.value = selectIntakeLine(values.value, id, selected);
  }
  function fill(context: ReceiptPreparation, id: string): void {
    if (!values.value) return;
    const replacement = prepareIntake(
      {
        ...context,
        lines: context.lines.filter((line) => line.documentLineId === id),
      },
      () => crypto.randomUUID(),
    ).rows;
    const first = values.value.rows.findIndex(
      (row) => row.documentLineId === id,
    );
    values.value.rows = values.value.rows.filter(
      (row) => row.documentLineId !== id,
    );
    values.value.rows.splice(Math.max(0, first), 0, ...replacement);
  }
  function accept(context: ReceiptPreparation): void {
    if (!values.value) return;
    values.value = rebaseIntake(values.value, context);
    errors.value = validateIntake(values.value);
  }
  return {
    values,
    errors,
    dirty,
    reset,
    initialize,
    change,
    remove,
    split,
    select,
    fill,
    accept,
  };
}
