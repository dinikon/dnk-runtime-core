import { computed, ref, onScopeDispose, watch, type Ref } from "vue";
import { useQueryClient } from "@tanstack/vue-query";
import type { ItemPackaging } from "./item-packaging.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import { useDeleteItemPackaging } from "./use-delete-item-packaging";
import { checkItemPackagingPresence } from "./use-check-item-packaging-presence";
import {
  forgetItemPackaging,
  discardItemPackagingContext,
  type DeleteItemPackagingInput,
} from "./item-packaging-removal";
import { ItemPackagingRequestError } from "./item-packaging.errors";
import { InventorySettingsRequestError } from "./inventory-item-settings.errors";

export interface ItemPackagingDeletionState {
  target: Ref<ItemPackaging | null>;
  pending: Ref<boolean>;
  uncertain: Ref<boolean>;
  error: Ref<string>;
  blocked: Ref<boolean>;
  removedId: Ref<string>;
  open(item: ItemPackaging): void;
  close(): void;
  confirm(): Promise<void>;
  check(): Promise<void>;
}

/** Локальное состояние подтверждения и восстановления; навигацией владеет Page. */
export function useItemPackagingDeletion(
  itemId: Ref<string>,
  identity: Ref<string>,
  scope: InventoryScopeState,
  onRemoved: (alreadyGone: boolean) => void,
): ItemPackagingDeletionState {
  const target = ref<ItemPackaging | null>(null),
    pending = ref(false),
    uncertain = ref(false),
    error = ref(""),
    blocked = ref(false),
    removedId = ref("");
  const id = computed(() => target.value?.id ?? "");
  const mutation = useDeleteItemPackaging(itemId, id, scope),
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
  function open(item: ItemPackaging): void {
    if (
      target.value ||
      pending.value ||
      blocked.value ||
      !scope.ready.value ||
      item.inventoryItemId !== itemId.value
    )
      return;
    target.value = { ...item };
    uncertain.value = false;
    error.value = "";
  }
  function close(): void {
    if (pending.value) return;
    target.value = null;
    uncertain.value = false;
    error.value = "";
  }
  function failure(cause: unknown, checking: boolean): void {
    const status =
      cause instanceof ItemPackagingRequestError ||
      cause instanceof InventorySettingsRequestError
        ? cause.status
        : null;
    if (status === 403 || (checking && status === 404)) {
      blocked.value = true;
      error.value =
        status === 403
          ? "Нет доступа к упаковкам товара."
          : "SKU не найден. Наличие упаковки не подтверждено.";
      target.value = null;
      return;
    }
    uncertain.value =
      checking ||
      !(cause instanceof ItemPackagingRequestError) ||
      cause.uncertain ||
      status === 404;
    error.value = uncertain.value
      ? "Результат удаления не подтверждён. Проверьте наличие упаковки перед новой попыткой."
      : cause instanceof Error
        ? cause.message
        : "Не удалось удалить упаковку.";
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
    const input: DeleteItemPackagingInput = {
      itemId: itemId.value,
      id: target.value.id,
      scope: [...scope.key.value],
      signal: controller.signal,
    };
    const relevant = (): boolean =>
      !controller.signal.aborted &&
      identity.value === captured &&
      scope.ready.value &&
      target.value?.id === input.id;
    request = controller;
    pending.value = true;
    error.value = "";
    let gone = false;
    try {
      if (checking) {
        const existing = await checkItemPackagingPresence(input);
        if (!relevant()) return;
        if (existing) {
          target.value = { ...existing };
          uncertain.value = false;
          error.value =
            "Упаковка существует. Для удаления подтвердите действие ещё раз.";
        } else {
          await forgetItemPackaging(cache, input, relevant);
          gone = relevant();
        }
      } else {
        await mutation.mutateAsync(input);
        gone = relevant();
      }
    } catch (cause: unknown) {
      if (relevant()) {
        failure(cause, checking);
        if (blocked.value)
          await discardItemPackagingContext(
            cache,
            input,
            () =>
              !controller.signal.aborted &&
              identity.value === captured &&
              scope.ready.value,
          );
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
    error,
    blocked,
    removedId,
    open,
    close,
    confirm: (): Promise<void> => run(false),
    check: (): Promise<void> => run(true),
  };
}
