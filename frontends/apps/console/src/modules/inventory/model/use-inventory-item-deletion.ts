import { computed, ref, watch, onScopeDispose, type Ref } from "vue";
import { useQueryClient } from "@tanstack/vue-query";
import { useDeleteInventoryItem } from "./use-delete-inventory-item";
import { checkInventoryItemPresence } from "./check-inventory-item-presence";
import {
  forgetInventoryItem,
  discardInaccessibleInventoryItem,
} from "./inventory-item-removal";
import { InventoryItemWriteError } from "./inventory-item-write.errors";
import { InventorySettingsRequestError } from "./inventory-item-settings.errors";
import type {
  InventoryItemDeleteTarget,
  InventoryItemMutationInput,
} from "./inventory-item-editor.types";
import type { InventoryScopeState } from "./use-inventory-scope";
export interface InventoryItemDeletionState {
  target: Ref<InventoryItemDeleteTarget | null>;
  pending: Ref<boolean>;
  uncertain: Ref<boolean>;
  blocked: Ref<boolean>;
  error: Ref<string>;
  removedId: Ref<string>;
  open(value: InventoryItemDeleteTarget): void;
  close(): void;
  confirm(): Promise<void>;
  check(): Promise<void>;
}
export function useInventoryItemDeletion(
  identity: Ref<string>,
  scope: InventoryScopeState,
  onRemoved: (alreadyGone: boolean) => void,
): InventoryItemDeletionState {
  const target = ref<InventoryItemDeleteTarget | null>(null),
    pending = ref(false),
    uncertain = ref(false),
    error = ref(""),
    blocked = ref(false),
    removedId = ref("");
  const id = computed(() => target.value?.id ?? ""),
    mutation = useDeleteInventoryItem(id, scope),
    cache = useQueryClient();
  let request: AbortController | null = null;
  function reset(): void {
    request?.abort();
    request = null;
    target.value = null;
    pending.value = false;
    uncertain.value = false;
    error.value = "";
    blocked.value = false;
    removedId.value = "";
    mutation.reset();
  }
  watch(identity, reset, { flush: "sync" });
  onScopeDispose(reset);
  function open(value: InventoryItemDeleteTarget): void {
    if (target.value || pending.value || blocked.value || !scope.ready.value)
      return;
    target.value = { id: value.id, sku: value.sku };
    error.value = "";
    uncertain.value = false;
  }
  function close(): void {
    if (pending.value) return;
    target.value = null;
    error.value = "";
    uncertain.value = false;
  }
  async function run(checking: boolean): Promise<void> {
    if (
      !target.value ||
      pending.value ||
      blocked.value ||
      !scope.ready.value ||
      (!checking && uncertain.value)
    )
      return;
    const captured = identity.value,
      controller = new AbortController();
    const input: InventoryItemMutationInput = {
      id: target.value.id,
      scope: [...scope.key.value],
      signal: controller.signal,
    };
    const contextRelevant = (): boolean =>
      !controller.signal.aborted &&
      captured === identity.value &&
      scope.ready.value;
    const relevant = (): boolean =>
      contextRelevant() && target.value?.id === input.id;
    request = controller;
    pending.value = true;
    error.value = "";
    let gone = false;
    try {
      if (checking) {
        const existing = await checkInventoryItemPresence(input);
        if (!relevant()) return;
        if (existing) {
          target.value = { id: existing.id, sku: existing.sku };
          uncertain.value = false;
          error.value =
            "Позиция существует. Для удаления подтвердите действие ещё раз.";
        } else {
          await forgetInventoryItem(cache, input, relevant);
          gone = relevant();
        }
      } else {
        await mutation.mutateAsync(input);
        gone = relevant();
      }
    } catch (cause: unknown) {
      if (relevant()) {
        const status =
          cause instanceof InventoryItemWriteError ||
          cause instanceof InventorySettingsRequestError
            ? cause.status
            : null;
        if (status === 403) {
          blocked.value = true;
          error.value = "Нет доступа к складской позиции.";
          target.value = null;
          await discardInaccessibleInventoryItem(cache, input, contextRelevant);
        } else {
          uncertain.value =
            checking ||
            !(cause instanceof InventoryItemWriteError) ||
            cause.uncertain ||
            status === 404;
          error.value = uncertain.value
            ? "Результат удаления не подтверждён. Проверьте наличие позиции перед новой попыткой."
            : cause instanceof Error
              ? cause.message
              : "Не удалось удалить позицию.";
        }
      }
    } finally {
      if (request === controller) {
        request = null;
        pending.value = false;
      }
    }
    if (gone) {
      removedId.value = input.id;
      target.value = null;
      uncertain.value = false;
      error.value = "";
      onRemoved(checking);
    }
  }
  return {
    target,
    pending,
    uncertain,
    blocked,
    error,
    removedId,
    open,
    close,
    confirm: (): Promise<void> => run(false),
    check: (): Promise<void> => run(true),
  };
}
