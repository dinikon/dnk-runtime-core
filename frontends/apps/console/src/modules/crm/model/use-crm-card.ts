import {
  computed,
  onBeforeUnmount,
  ref,
  shallowRef,
  watch,
  type Ref,
} from "vue";
import {
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
  useRoute,
  useRouter,
} from "vue-router";
import { useQueryClient } from "@tanstack/vue-query";
import { getApiErrorMessage } from "@/app/providers/http";

/** Keep a card draft stable while query invalidation refreshes the surrounding lists. */
export function useCrmCard<T>(
  kind: "contacts" | "companies",
  get: (id: string, signal?: AbortSignal) => Promise<T>,
  pending: Ref<boolean>,
) {
  const route = useRoute();
  const router = useRouter();
  const client = useQueryClient();
  const cardId = computed(() =>
    typeof route.query.card === "string" ? route.query.card : "",
  );
  const editing = shallowRef<T | null>(null);
  const formOpen = ref(false);
  const dirty = ref(false);
  const loading = ref(false);
  const loadError = ref("");
  const conflict = ref(false);
  const discardOpen = ref(false);
  let resolveDiscard: ((approved: boolean) => void) | undefined;
  let generation = 0;

  function decideDiscard(approved: boolean) {
    discardOpen.value = false;
    resolveDiscard?.(approved);
    resolveDiscard = undefined;
  }
  async function canDiscard() {
    if (pending.value) return false;
    if (!dirty.value) return true;
    // Keep a single pending decision even if navigation is requested twice.
    if (resolveDiscard) return false;
    discardOpen.value = true;
    const approved = await new Promise<boolean>((resolve) => {
      resolveDiscard = resolve;
    });
    if (approved) dirty.value = false;
    return approved;
  }
  async function load(id: string) {
    const request = ++generation;
    formOpen.value = false;
    editing.value = null;
    conflict.value = false;
    dirty.value = false;
    loadError.value = "";
    if (!id) {
      loading.value = false;
      return;
    }
    loading.value = true;
    try {
      const item = await client.fetchQuery({
        queryKey: ["crm", kind, "detail", id],
        queryFn: ({ signal }) => get(id, signal),
        staleTime: 0,
      });
      if (request !== generation) return;
      editing.value = item;
      formOpen.value = true;
    } catch (error) {
      if (request === generation)
        loadError.value = getApiErrorMessage(
          error,
          "Не удалось загрузить карточку.",
        );
    } finally {
      if (request === generation) loading.value = false;
    }
  }
  watch(
    cardId,
    (id) => {
      void load(id);
    },
    { immediate: true },
  );
  onBeforeRouteLeave(() => canDiscard());
  onBeforeRouteUpdate((to) =>
    to.query.card === route.query.card ? true : canDiscard(),
  );
  function beforeUnload(event: BeforeUnloadEvent) {
    if (dirty.value || pending.value) {
      event.preventDefault();
      event.returnValue = "";
    }
  }
  window.addEventListener("beforeunload", beforeUnload);
  onBeforeUnmount(() => {
    ++generation;
    window.removeEventListener("beforeunload", beforeUnload);
    decideDiscard(false);
  });
  async function openCreate() {
    if (!(await canDiscard())) return;
    if (cardId.value)
      await router.replace({ query: { ...route.query, card: undefined } });
    editing.value = null;
    conflict.value = false;
    formOpen.value = true;
  }
  function openEdit(item: { id: string }) {
    return router.push({ query: { ...route.query, card: item.id } });
  }
  async function close() {
    if (!(await canDiscard())) return;
    formOpen.value = false;
    editing.value = null;
    if (cardId.value)
      await router.replace({ query: { ...route.query, card: undefined } });
  }
  async function saved() {
    dirty.value = false;
    conflict.value = false;
    formOpen.value = false;
    editing.value = null;
    await router.replace({ query: { ...route.query, card: undefined } });
  }
  async function reload() {
    if (await canDiscard()) await load(cardId.value);
  }
  function navigate(id: string) {
    return router.push({
      name: kind === "contacts" ? "crm-companies" : "crm-contacts",
      query: { card: id },
    });
  }
  return {
    editing,
    formOpen,
    dirty,
    loading,
    loadError,
    conflict,
    discardOpen,
    decideDiscard,
    openCreate,
    openEdit,
    close,
    saved,
    reload,
    navigate,
  };
}
