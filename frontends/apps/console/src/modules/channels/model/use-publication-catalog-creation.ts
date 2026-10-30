import { onBeforeUnmount, ref, watch, type Ref } from "vue";
import type { CreatePublicationCatalogResult } from "./catalog-creation.types";
import { publicationCatalogError } from "./catalog-creation.errors";
import { useCreatePublicationCatalog } from "./use-create-publication-catalog";

/** Единый сценарий создания из строки списка и из карточки с защитой контекста. */
export function usePublicationCatalogCreation(
  channelId: Ref<string>,
  context: Ref<string>,
): {
  pending: Ref<boolean>;
  error: Ref<string>;
  warnings: Ref<string[]>;
  create(publicationId: string): Promise<CreatePublicationCatalogResult | null>;
} {
  const mutation = useCreatePublicationCatalog();
  const pending = ref(false),
    error = ref(""),
    warnings = ref<string[]>([]);
  let mounted = true;
  onBeforeUnmount(() => {
    mounted = false;
  });
  watch(context, () => {
    pending.value = false;
    error.value = "";
    warnings.value = [];
    mutation.reset();
  });
  async function create(
    publicationId: string,
  ): Promise<CreatePublicationCatalogResult | null> {
    if (pending.value || !channelId.value || !publicationId) return null;
    const captured = context.value;
    const relevant = (): boolean => mounted && context.value === captured;
    pending.value = true;
    error.value = "";
    warnings.value = [];
    try {
      const created = await mutation.mutateAsync({
        channelId: channelId.value,
        publicationId,
      });
      if (!relevant()) return null;
      warnings.value = created.warnings;
      return created;
    } catch (cause) {
      if (relevant()) error.value = publicationCatalogError(cause);
      return null;
    } finally {
      if (relevant()) pending.value = false;
    }
  }
  return { pending, error, warnings, create };
}
