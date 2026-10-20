import { computed, ref, watch, type ComputedRef, type Ref } from "vue";
import type { ChannelsContext } from "./use-channels-context";
import type {
  ImportDraftValues,
  PublicationImport,
} from "./publication-import.types";
import type { CreateDraftInput } from "./catalog-links.types";
import { editableDraft } from "./draft-form";
import {
  copyImportValues,
  restorePublicationImportDraft,
} from "./publication-import-draft";
export interface PublicationImportDraftState {
  values: Ref<ImportDraftValues | null>;
  intent: Ref<CreateDraftInput | null>;
  uncertain: Ref<boolean>;
  dirty: ComputedRef<boolean>;
  hydrate: (preparation: PublicationImport) => void;
  submit: (input: CreateDraftInput) => void;
  reject: () => void;
  clear: () => void;
}
export function usePublicationImportDraft(
  ctx: ChannelsContext,
  identifier: ComputedRef<string>,
): PublicationImportDraftState {
  const values = ref<ImportDraftValues | null>(null),
    intent = ref<CreateDraftInput | null>(null),
    uncertain = ref(false),
    baseline = ref(""),
    expiresAt = ref("");
  const key = computed(
    () =>
      `channels:publication-import:v1:${ctx.scope.value}:${identifier.value}`,
  );
  function remove(storageKey: string): void {
    try {
      sessionStorage.removeItem(storageKey);
    } catch {
      /* Storage may be unavailable. */
    }
  }
  watch(
    key,
    (next, previous) => {
      if (
        previous &&
        previous.split(":").slice(0, -1).join(":") !==
          next.split(":").slice(0, -1).join(":")
      )
        remove(previous);
      let restored = null;
      try {
        restored = restorePublicationImportDraft(sessionStorage.getItem(next));
      } catch {
        /* Keep the in-memory flow usable. */
      }
      values.value = restored?.values ?? null;
      intent.value = restored?.intent ?? null;
      uncertain.value = restored?.uncertain ?? false;
      baseline.value = restored?.baseline ?? "";
      expiresAt.value = restored?.expiresAt ?? "";
    },
    { immediate: true, flush: "sync" },
  );
  watch(
    [values, intent, uncertain, baseline, expiresAt],
    () => {
      if (!values.value || !expiresAt.value) return;
      try {
        sessionStorage.setItem(
          key.value,
          JSON.stringify({
            version: 1,
            values: values.value,
            intent: intent.value,
            uncertain: uncertain.value,
            baseline: baseline.value,
            expiresAt: expiresAt.value,
          }),
        );
      } catch {
        /* Retain the current form if browser storage is full. */
      }
    },
    { deep: true, flush: "sync" },
  );
  function hydrate(preparation: PublicationImport): void {
    if (!values.value && preparation.values) {
      values.value = copyImportValues(
        editableDraft(preparation.values) as ImportDraftValues,
      );
      baseline.value = JSON.stringify(values.value);
      expiresAt.value = preparation.expiresAt;
    }
  }
  function submit(input: CreateDraftInput): void {
    intent.value = {
      ...input,
      values: {
        ...input.values,
        titles: { ...input.values.titles },
        descriptions: { ...input.values.descriptions },
        gallery: [...(input.values.gallery ?? [])],
      },
    };
    uncertain.value = true;
  }
  function reject(): void {
    uncertain.value = false;
    intent.value = null;
  }
  function clear(): void {
    values.value = null;
    intent.value = null;
    uncertain.value = false;
    baseline.value = "";
    expiresAt.value = "";
    remove(key.value);
  }
  return {
    values,
    intent,
    uncertain,
    dirty: computed(
      () => !!values.value && JSON.stringify(values.value) !== baseline.value,
    ),
    hydrate,
    submit,
    reject,
    clear,
  };
}
