import { computed, ref, watch, type Ref, type ComputedRef } from "vue";
import { useQueryClient } from "@tanstack/vue-query";
import { useFeed } from "./feed.queries";
import { useFeedScope } from "./use-feed-scope";
import { useCreateFeed } from "./use-create-feed";
import { useUpdateFeed } from "./use-update-feed";
import { feedKeys } from "./feed.query-keys";
import {
  feedDraft,
  draftSettings,
  feedChanges,
  acknowledgeFeedDraft,
  validateFeedDraft,
} from "./feed.draft";
import {
  FeedApiError,
  type Feed,
  type FeedDraft,
  type FeedFieldErrors,
} from "./feed.types";
import { feedErrorMessage, isUncertainCreate } from "./feed.errors";
export interface FeedEditor {
  query: ReturnType<typeof useFeed>;
  draft: Ref<FeedDraft | null>;
  base: Ref<Feed | null>;
  contextKey: ComputedRef<string>;
  dirty: ComputedRef<boolean>;
  busy: ComputedRef<boolean>;
  readonly: ComputedRef<boolean>;
  conflict: Ref<boolean>;
  uncertain: Ref<boolean>;
  error: ComputedRef<string>;
  fields: ComputedRef<FeedFieldErrors>;
  save(): Promise<string | undefined>;
  reset(): void;
  acknowledgeArchive(): void;
}
export function useFeedEditor(id: Ref<string>): FeedEditor {
  const scope = useFeedScope(),
    query = useFeed(id),
    client = useQueryClient();
  const create = useCreateFeed(),
    update = useUpdateFeed();
  const draft = ref<FeedDraft | null>(null),
    base = ref<Feed | null>(null),
    baseline = ref("");
  const conflict = ref(false),
    uncertain = ref(false);
  const contextKey = computed(() => JSON.stringify([scope.value, id.value]));
  const dirty = computed(
    () => !!draft.value && JSON.stringify(draft.value) !== baseline.value,
  );
  const busy = computed(() => create.pending.value || update.pending.value);
  const readonly = computed(() => query.data.value?.status === "ARCHIVED");
  const failure = computed(() =>
    id.value ? update.error.value : create.error.value,
  );
  const error = computed(() =>
    failure.value ? feedErrorMessage(failure.value, !id.value) : "",
  );
  const fields = computed(() =>
    failure.value instanceof FeedApiError ? failure.value.fields : {},
  );
  function install(feed?: Feed): void {
    draft.value = feedDraft(feed);
    baseline.value = JSON.stringify(draft.value);
    base.value = feed ?? null;
    conflict.value = false;
  }
  watch(
    contextKey,
    () => {
      draft.value = null;
      base.value = null;
      baseline.value = "";
      conflict.value = false;
      uncertain.value = false;
      create.error.value = undefined;
      update.error.value = undefined;
      if (!id.value && scope.value[0] && scope.value[1]) install();
    },
    { immediate: true, flush: "sync" },
  );
  watch(
    query.data,
    (feed) => {
      if (!feed || !id.value) return;
      if (!draft.value) install(feed);
      else if (base.value?.version !== feed.version) {
        if (dirty.value || conflict.value) conflict.value = true;
        else install(feed);
      }
    },
    { immediate: true },
  );
  function reset(): void {
    if (id.value && !query.data.value) return;
    install(id.value ? query.data.value : undefined);
    create.error.value = undefined;
    update.error.value = undefined;
  }
  async function save(): Promise<string | undefined> {
    if (
      !draft.value ||
      busy.value ||
      readonly.value ||
      conflict.value ||
      uncertain.value ||
      Object.keys(validateFeedDraft(draft.value)).length
    )
      return;
    const captured = contextKey.value,
      sent = { ...draft.value },
      settings = draftSettings(sent);
    if (id.value && !base.value) return;
    if (
      id.value &&
      base.value &&
      !Object.keys(feedChanges(base.value, settings)).length
    ) {
      install(base.value);
      return id.value;
    }
    const result =
      id.value && base.value
        ? await update.execute({
            id: id.value,
            expectedVersion: base.value.version,
            changes: feedChanges(base.value, settings),
          })
        : await create.execute(settings);
    if (captured !== contextKey.value) return;
    if (!result) {
      if (
        failure.value instanceof FeedApiError &&
        failure.value.status === 409 &&
        id.value
      )
        conflict.value = true;
      if (!id.value && failure.value && isUncertainCreate(failure.value))
        uncertain.value = true;
      return;
    }
    const saved = result.value;
    draft.value = acknowledgeFeedDraft(draft.value!, sent, saved);
    base.value = saved;
    baseline.value = JSON.stringify(feedDraft(saved));
    conflict.value = false;
    client.setQueryData(feedKeys.detail(scope.value, saved.id), saved);
    return saved.id;
  }
  function acknowledgeArchive(): void {
    baseline.value = JSON.stringify(draft.value);
  }
  return {
    query,
    draft,
    base,
    contextKey,
    dirty,
    busy,
    readonly,
    conflict,
    uncertain,
    error,
    fields,
    save,
    reset,
    acknowledgeArchive,
  };
}
