import { cloneSchemaValue } from "./feed-schema.clone";
import { computed, ref, watch, type Ref, type ComputedRef } from "vue";
import { useQueryClient } from "@tanstack/vue-query";
import { useFeedScope } from "./use-feed-scope";
import { useFeedSchema, useSchemaMetadata } from "./feed-schema.queries";
import { useSaveFeedSchema } from "./use-save-feed-schema";
import { feedSchemaKeys } from "./feed-schema.query-keys";
import {
  schemaDraft,
  newSchemaField,
  duplicateSchemaField,
  moveSchemaField,
  validateSchemaDraft,
  draftDefinition,
  acknowledgeSchemaDraft,
} from "./feed-schema.draft";
import { FeedApiError } from "./feed.types";
import {
  SchemaApiError,
  type FeedSchema,
  type FeedSchemaDraft,
  type SchemaFieldDraft,
  type FieldKind,
  type SchemaIssue,
} from "./feed-schema.types";
export interface FeedSchemaEditor {
  query: ReturnType<typeof useFeedSchema>;
  metadata: ReturnType<typeof useSchemaMetadata>;
  draft: Ref<FeedSchemaDraft | null>;
  selectedId: Ref<string>;
  selected: ComputedRef<SchemaFieldDraft | undefined>;
  contextKey: ComputedRef<string>;
  baseVersion: ComputedRef<number | null>;
  dirty: ComputedRef<boolean>;
  busy: Ref<boolean>;
  readonly: ComputedRef<boolean>;
  conflict: Ref<boolean>;
  issues: ComputedRef<SchemaIssue[]>;
  error: Ref<unknown>;
  add(kind: FieldKind): void;
  duplicate(id: string): void;
  remove(id: string): void;
  move(id: string, delta: number): void;
  change(field: SchemaFieldDraft): void;
  savedCategoryIds: ComputedRef<string[]>;
  reset(): void;
  save(): Promise<boolean>;
}
export function useFeedSchemaEditor(id: Ref<string>): FeedSchemaEditor {
  const scope = useFeedScope(),
    query = useFeedSchema(id),
    metadata = useSchemaMetadata(),
    action = useSaveFeedSchema(),
    client = useQueryClient();
  const draft = ref<FeedSchemaDraft | null>(null),
    base = ref<FeedSchema | null>(null),
    baseline = ref(""),
    selectedId = ref(""),
    conflict = ref(false),
    localIssues = ref<SchemaIssue[]>([]);
  const contextKey = computed(() => JSON.stringify([scope.value, id.value]));
  const dirty = computed(
    () => !!draft.value && JSON.stringify(draft.value) !== baseline.value,
  );
  const readonly = computed(() => query.data.value?.status === "ARCHIVED");
  const selected = computed(() =>
    draft.value?.fields.find((f) => f.id === selectedId.value),
  );
  const issues = computed(() => [
    ...localIssues.value,
    ...(action.error.value instanceof SchemaApiError
      ? action.error.value.issues
      : []),
  ]);
  function install(value: FeedSchema): void {
    base.value = value;
    draft.value = schemaDraft(value.definition);
    baseline.value = JSON.stringify(draft.value);
    conflict.value = false;
    localIssues.value = [];
    if (!draft.value.fields.some((f) => f.id === selectedId.value))
      selectedId.value = draft.value.fields[0]?.id ?? "";
  }
  watch(
    contextKey,
    () => {
      draft.value = null;
      base.value = null;
      baseline.value = "";
      selectedId.value = "";
      conflict.value = false;
      localIssues.value = [];
      action.error.value = undefined;
    },
    { flush: "sync" },
  );
  watch(
    [query.data, contextKey],
    () => {
      const value = client.getQueryData<FeedSchema>(
        feedSchemaKeys.detail(scope.value, id.value),
      );
      if (
        !scope.value[0] ||
        !scope.value[1] ||
        !value ||
        value.feedId !== id.value
      )
        return;
      if (!draft.value) install(value);
      else if (base.value?.version !== value.version) {
        if (dirty.value || conflict.value) conflict.value = true;
        else install(value);
      }
    },
    { immediate: true },
  );
  function editable(): boolean {
    return (
      !!draft.value &&
      !readonly.value &&
      !action.pending.value &&
      !conflict.value
    );
  }
  function clearErrors(): void {
    localIssues.value = [];
    action.error.value = undefined;
  }
  function add(kind: FieldKind): void {
    if (
      !editable() ||
      !metadata.data.value ||
      draft.value!.fields.length >= metadata.data.value.maxFields ||
      !metadata.data.value.fieldTypes.some((t) => t.kind === kind)
    )
      return;
    const field = newSchemaField(
      kind,
      crypto.randomUUID(),
      draft.value!.fields,
      metadata.data.value.locales[0]?.code,
    );
    draft.value!.fields.push(field);
    selectedId.value = field.id;
    clearErrors();
  }
  function duplicate(identifier: string): void {
    if (
      !editable() ||
      !metadata.data.value ||
      draft.value!.fields.length >= metadata.data.value.maxFields
    )
      return;
    const field = draft.value!.fields.find((f) => f.id === identifier);
    if (!field) return;
    const clone = duplicateSchemaField(
      field,
      crypto.randomUUID(),
      draft.value!.fields,
    );
    draft.value!.fields.splice(
      draft.value!.fields.indexOf(field) + 1,
      0,
      clone,
    );
    selectedId.value = clone.id;
    clearErrors();
  }
  function remove(identifier: string): void {
    if (!editable()) return;
    const index = draft.value!.fields.findIndex((f) => f.id === identifier);
    if (index < 0) return;
    draft.value!.fields.splice(index, 1);
    if (selectedId.value === identifier)
      selectedId.value =
        draft.value!.fields[Math.min(index, draft.value!.fields.length - 1)]
          ?.id ?? "";
    clearErrors();
  }
  function move(identifier: string, delta: number): void {
    if (!editable()) return;
    draft.value!.fields = moveSchemaField(
      draft.value!.fields,
      identifier,
      delta,
    );
    clearErrors();
  }
  function change(field: SchemaFieldDraft): void {
    if (!editable()) return;
    const index = draft.value!.fields.findIndex((f) => f.id === field.id);
    if (index < 0) return;
    draft.value!.fields[index] = field;
    if (field.categoryTreeId && field.typeDefinition.kind === "category") {
      for (const other of draft.value!.fields) {
        if (other.id !== field.id && other.categoryTreeId === field.categoryTreeId)
          other.typeDefinition = cloneSchemaValue(field.typeDefinition);
      }
    }
    clearErrors();
  }
  function reset(): void {
    if (query.data.value) {
      install(query.data.value);
      action.error.value = undefined;
    }
  }
  async function save(): Promise<boolean> {
    if (!editable() || !base.value || !metadata.data.value) return false;
    localIssues.value = validateSchemaDraft(draft.value!, metadata.data.value);
    action.error.value = undefined;
    if (localIssues.value.length) {
      const first = localIssues.value.find((i) => i.fieldId);
      if (first) selectedId.value = first.fieldId!;
      return false;
    }
    const captured = contextKey.value,
      sent = cloneSchemaValue(draft.value!);
    const result = await action.execute({
      id: id.value,
      expectedVersion: base.value.version,
      definition: draftDefinition(sent, metadata.data.value),
    });
    if (captured !== contextKey.value) return false;
    if (!result) {
      if (
        action.error.value instanceof FeedApiError &&
        action.error.value.status === 409
      )
        conflict.value = true;
      return false;
    }
    draft.value = acknowledgeSchemaDraft(
      draft.value!,
      sent,
      result.value.definition,
    );
    baseline.value = JSON.stringify(schemaDraft(result.value.definition));
    base.value = {
      ...base.value!,
      version: result.value.version,
      definition: result.value.definition,
    };
    client.setQueryData(
      feedSchemaKeys.detail(scope.value, id.value),
      base.value,
    );
    conflict.value = false;
    return true;
  }
  return {
    query,
    metadata,
    draft,
    selectedId,
    selected,
    contextKey,
    baseVersion: computed(() => base.value?.version ?? null),
    dirty,
    busy: action.pending,
    readonly,
    conflict,
    issues,
    error: action.error,
    add,
    savedCategoryIds: computed(() => {
      const type = base.value?.definition.fields.find(field => field.id === selectedId.value)?.typeDefinition;
      return type?.kind === "category" ? type.value.nodes.map(node => node.id) : [];
    }),
    duplicate,
    remove,
    move,
    change,
    reset,
    save,
  };
}
