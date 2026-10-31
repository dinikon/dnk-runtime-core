import { computed, ref, watch, type Ref, type ComputedRef } from "vue";
import { useChannel, useChannelPlatforms } from "./channel.queries";
import { useSaveChannel } from "./use-save-channel";
import { useVerifyChannel } from "./use-verify-channel";
import { useDeleteChannel } from "./use-delete-channel";
import { useChannelScope } from "./use-channel-scope";
import { draftFor, saveDraft } from "./channel.schema";
import type { ChannelDraft } from "./channel.types";

interface ChannelEditor {
  query: ReturnType<typeof useChannel>;
  platforms: ReturnType<typeof useChannelPlatforms>;
  draft: Ref<ChannelDraft | null>;
  baseRevision: Ref<number>;
  contextKey: ComputedRef<string>;
  platform: ComputedRef<import("./channel.types").Platform | undefined>;
  busy: ComputedRef<boolean>;
  dirty: ComputedRef<boolean>;
  error: ComputedRef<string>;
  deleteError: Ref<string>;
  resetDraft(): void;
  changePlatform(kind: string): void;
  save(): Promise<string | undefined>;
  verify(): Promise<void>;
  remove(): Promise<boolean>;
}

export function useChannelEditor(id: Ref<string>): ChannelEditor {
  const scope = useChannelScope();
  const query = useChannel(id),
    platforms = useChannelPlatforms();
  const saveAction = useSaveChannel(),
    verifyAction = useVerifyChannel(),
    deleteAction = useDeleteChannel();
  const draft = ref<ChannelDraft | null>(null),
    baseRevision = ref(0);
  let loadedKey = "",
    baseline = "",
    baselineConfigRevision = 0;
  const contextKey = computed(() => JSON.stringify([scope.value, id.value]));
  function fingerprint(value: ChannelDraft): string {
    return JSON.stringify([
      value.name,
      value.platformKind,
      value.endpoint,
      value.settings,
    ]);
  }
  watch(
    contextKey,
    () => {
      loadedKey = "";
      draft.value = null;
    },
    { flush: "sync" },
  );
  function resetDraft(): void {
    const channel = id.value ? query.data.value : undefined;
    if (id.value && !channel) return;
    const installed =
      platforms.data.value?.find((p) => p.kind === channel?.platformKind) ??
      (!id.value ? platforms.data.value?.[0] : undefined);
    if (!installed) return;
    draft.value = draftFor(installed, channel);
    baseRevision.value = channel?.revision ?? 0;
    baselineConfigRevision = channel?.configRevision ?? 0;
    baseline = fingerprint(draft.value);
    loadedKey = contextKey.value;
  }
  watch(
    [platforms.data, query.data, contextKey],
    () => {
      if (loadedKey !== contextKey.value) resetDraft();
      else {
        const channel = query.data.value;
        const installed = platforms.data.value?.find(
          (p) => p.kind === channel?.platformKind,
        );
        if (
          channel &&
          installed &&
          channel.configRevision === baselineConfigRevision &&
          fingerprint(draftFor(installed, channel)) === baseline
        )
          baseRevision.value = channel.revision;
      }
    },
    { immediate: true, flush: "post" },
  );
  const platform = computed(() =>
    platforms.data.value?.find((p) => p.kind === draft.value?.platformKind),
  );
  const busy = computed(
    () =>
      saveAction.pending.value ||
      verifyAction.pending.value ||
      deleteAction.pending.value,
  );
  const dirty = computed(
    () =>
      !!draft.value &&
      (fingerprint(draft.value) !== baseline ||
        (!!id.value && draft.value.replaceCredentials) ||
        Object.values(draft.value.credentials).some(Boolean)),
  );
  const error = computed(
    () => saveAction.error.value || verifyAction.error.value,
  );
  function changePlatform(kind: string): void {
    const next = platforms.data.value?.find((p) => p.kind === kind);
    if (next && !id.value && draft.value)
      draft.value = { ...draftFor(next), name: draft.value.name };
  }
  async function save(): Promise<string | undefined> {
    if (!draft.value || !platform.value || busy.value) return;
    const captured = contextKey.value;
    const result = await saveAction.execute({
      id: id.value || undefined,
      revision: baseRevision.value,
      value: saveDraft(draft.value, platform.value),
    });
    if (!result || contextKey.value !== captured) return;
    if (id.value) resetDraft();
    else {
      draft.value = null;
      loadedKey = "";
    }
    return result.value.id;
  }
  async function verify(): Promise<void> {
    if (id.value && !dirty.value && !busy.value)
      await verifyAction.execute(id.value);
  }
  async function remove(): Promise<boolean> {
    if (!query.data.value || busy.value) return false;
    const captured = contextKey.value;
    const result = await deleteAction.execute({
      id: id.value,
      revision: query.data.value.revision,
    });
    if (!result || contextKey.value !== captured) return false;
    draft.value = null;
    return true;
  }
  return {
    query,
    platforms,
    draft,
    baseRevision,
    contextKey,
    platform,
    busy,
    dirty,
    error,
    deleteError: deleteAction.error,
    resetDraft,
    changePlatform,
    save,
    verify,
    remove,
  };
}
