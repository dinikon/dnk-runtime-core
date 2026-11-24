import { computed, ref, watch, type Ref } from "vue";
import { useQueryClient } from "@tanstack/vue-query";
import { publicationFieldsApi } from "../api/publication-fields.api";
import { feedPreviewKeys } from "./feed-preview.query-keys";
import { publicationKeys } from "./feed-publication.query-keys";
import { parseFeedInteger } from "./feed-schema.draft";
import { SchemaApiError } from "./feed-schema.types";
import { useFeedAction } from "./use-feed-action";
import { useFeedScope } from "./use-feed-scope";
import { usePublicationFields } from "./use-publication-fields";
import type {
  PublicationField,
  PublicationFieldValue,
  PublicationOverrideDraft,
  PublicationOverrideTarget,
} from "./publication-fields.types";

export function usePublicationOverrideEditor(
  feedId: Ref<string>,
  publicationId: Ref<string>,
) {
  const scope = useFeedScope();
  const cache = useQueryClient();
  const query = usePublicationFields(feedId, publicationId);
  const set = useFeedAction(publicationFieldsApi.set);
  const reset = useFeedAction(publicationFieldsApi.reset);
  const draft = ref<PublicationOverrideDraft>();
  const error = ref<{ fieldId: string; message: string }>();
  const updating = ref(false);
  const pending = computed(
    () => updating.value || set.pending.value || reset.pending.value,
  );
  let revision = 0;

  watch(
    () => [scope.value, feedId.value, publicationId.value] as const,
    () => {
      revision++;
      draft.value = undefined;
      error.value = undefined;
      updating.value = false;
    },
    { flush: "sync" },
  );

  const activeField = computed(() =>
    query.data.value?.fields.find(
      (field) => field.id === draft.value?.field.id,
    ),
  );
  const conflict = computed(() =>
    Boolean(
      draft.value &&
      query.data.value &&
      (draft.value.target.feedVersion !== query.data.value.feedVersion ||
        draft.value.target.publicationVersion !==
          query.data.value.publicationVersion),
    ),
  );

  function target(fieldId: string): PublicationOverrideTarget | undefined {
    const current = query.data.value;
    if (
      !current ||
      current.readonly ||
      query.isError.value ||
      !publicationId.value
    )
      return;
    return {
      publicationId: publicationId.value,
      fieldId,
      feedVersion: current.feedVersion,
      publicationVersion: current.publicationVersion,
    };
  }

  function start(field: PublicationField): void {
    const current = target(field.id);
    if (!current || pending.value || draft.value) return;
    error.value = undefined;
    draft.value = { field, target: current, value: String(field.overrideValue ?? "") };
  }

  function update(value: string): void {
    if (!draft.value || pending.value) return;
    draft.value.value = value;
    error.value = undefined;
  }

  function acceptCurrent(): void {
    const field = activeField.value;
    const current = field && target(field.id);
    if (!field || !current || !draft.value || pending.value) return;
    draft.value = { field, target: current, value: draft.value.value };
    error.value = undefined;
  }

  function cancel(): void {
    if (pending.value) return;
    draft.value = undefined;
    error.value = undefined;
  }

  async function persist(
    current: PublicationOverrideTarget,
    value?: PublicationFieldValue,
  ): Promise<void> {
    if (pending.value) return;
    const startedAt = revision;
    updating.value = true;
    error.value = undefined;
    try {
      const action = value === undefined ? reset : set;
      const result =
        value === undefined
          ? await reset.execute(current)
          : await set.execute({ ...current, value });
      if (revision !== startedAt) return;
      if (!result) {
        const reason = action.error.value;
        error.value = {
          fieldId: current.fieldId,
          message:
            reason instanceof SchemaApiError
              ? (reason.issues[0]?.message ??
                "Проверьте значение и повторите действие.")
              : "Не удалось подтвердить изменение. Обновите карточку перед повтором.",
        };
        return;
      }
      draft.value = undefined;
      await Promise.all([
        query.refetch(),
        cache.invalidateQueries({
          queryKey: publicationKeys.listScope(scope.value, feedId.value),
        }),
        cache.invalidateQueries({
          queryKey: publicationKeys.detailScope(
            scope.value,
            publicationId.value,
          ),
        }),
        cache.invalidateQueries({
          queryKey: feedPreviewKeys.feed(scope.value, feedId.value),
        }),
      ]);
    } finally {
      if (revision === startedAt) updating.value = false;
    }
  }

  async function save(): Promise<void> {
    const current = draft.value;
    if (
      !current ||
      conflict.value ||
      !activeField.value ||
      !target(current.field.id)
    )
      return;
    let value: PublicationFieldValue = current.value;
    if (current.field.kind === "money") value = current.value.replace(",", ".");
    if (current.field.kind === "integer") {
      const parsed = parseFeedInteger(current.value);
      if (parsed === undefined) {
        error.value = { fieldId: current.field.id, message: "Введите целое число." };
        return;
      }
      value = parsed;
    }
    if (current.field.kind === "boolean") {
      if (value !== "true" && value !== "false") {
        error.value = { fieldId: current.field.id, message: "Выберите true или false." };
        return;
      }
      value = value === "true";
    }
    await persist(current.target, value);
  }

  async function restore(fieldId: string): Promise<void> {
    const current = target(fieldId);
    if (!current || draft.value) return;
    await persist(current);
  }

  return {
    query,
    draft,
    error,
    pending,
    activeField,
    conflict,
    start,
    update,
    acceptCurrent,
    cancel,
    save,
    restore,
  };
}
