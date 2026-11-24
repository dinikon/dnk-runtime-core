import {
  computed,
  ref,
  watch,
  onScopeDispose,
  onMounted,
  type Ref,
  type ComputedRef,
} from "vue";
import {
  useCalculationMetadata,
  useCalculationProducts,
  useCalculationVariants,
} from "./feed-calculation.queries";
import { useFeedCalculationSource } from "./use-feed-calculation-source";
import { feedCalculationApi } from "../api/feed-calculation.api";
import { useFeedScope } from "./use-feed-scope";
import { cloneSchemaValue } from "./feed-schema.clone";
import { draftDefinition, fieldCanPreview } from "./feed-schema.draft";
import type { SchemaFieldDraft, SchemaMetadata } from "./feed-schema.types";
import type { CalculationPreview } from "./feed-calculation.types";
export interface FeedCalculationPreview {
  metadata: ReturnType<typeof useCalculationMetadata>;
  products: ReturnType<typeof useCalculationProducts>;
  variants: ReturnType<typeof useCalculationVariants>;
  locale: Ref<string>;
  search: Ref<string>;
  offset: Ref<number>;
  variantOffset: Ref<number>;
  root: ReturnType<typeof useFeedCalculationSource>["root"];
  variant: ReturnType<typeof useFeedCalculationSource>["variant"];
  result: Ref<CalculationPreview | null>;
  error: Ref<unknown>;
  pending: Ref<boolean>;
  stale: Ref<boolean>;
  canPreview: ComputedRef<boolean>;
  preview(): Promise<void>;
}
export function useFeedCalculationPreview(
  feedId: Ref<string>,
  version: Ref<number | null>,
  field: Ref<SchemaFieldDraft | undefined>,
  schemaMetadata: Ref<SchemaMetadata | undefined>,
  blocked: Ref<boolean>,
  loadCatalogChoices?: Ref<boolean>,
): FeedCalculationPreview {
  const scope = useFeedScope(),
    source = useFeedCalculationSource();
  const { search, offset, variantOffset, root, variant } = source;
  const active = computed(() => !!scope.value[0] && !!scope.value[1]);
  const locale = ref("uk");
  watch(
    () => schemaMetadata.value?.locales,
    (locales) => {
      if (locales?.length && !locales.some((l) => l.code === locale.value))
        locale.value = locales[0]!.code;
    },
    { immediate: true },
  );
  const metadata = useCalculationMetadata(loadCatalogChoices);
  const products = useCalculationProducts(
    locale,
    search,
    offset,
    computed(
      () =>
        fieldCanPreview(field.value) &&
        (loadCatalogChoices?.value ?? true),
    ),
  );
  const variants = useCalculationVariants(
    computed(() =>
      root.value?.kind === "variable" && (loadCatalogChoices?.value ?? true)
        ? root.value.id
        : undefined,
    ),
    locale,
    variantOffset,
  );
  const result = ref<CalculationPreview | null>(null),
    error = ref<unknown>(),
    pending = ref(false),
    stale = ref(false);
  let sequence = 0,
    controller: AbortController | undefined,
    timer: ReturnType<typeof setTimeout> | undefined;
  function cancel(): void {
    sequence++;
    controller?.abort();
    controller = undefined;
    pending.value = false;
    if (timer) clearTimeout(timer);
    timer = undefined;
  }
  const context = computed(() => JSON.stringify([scope.value, feedId.value]));
  const signature = computed(() =>
    JSON.stringify([
      context.value,
      version.value,
      field.value,
      root.value?.id,
      variant.value?.id,
      blocked.value,
    ]),
  );
  watch(
    signature,
    () => {
      cancel();
      stale.value = !!result.value;
      error.value = undefined;
    },
    { flush: "sync" },
  );
  watch(
    context,
    () => {
      result.value = null;
      stale.value = false;
      source.reset();
    },
    { flush: "sync" },
  );
  const canPreview = computed(
    () =>
      active.value &&
      !blocked.value &&
      !pending.value &&
      version.value !== null &&
      !!schemaMetadata.value &&
      fieldCanPreview(field.value) &&
      !!root.value &&
      (root.value.kind === "simple" || !!variant.value),
  );
  function expireAtBoundary(value: CalculationPreview): void {
    if (!value.validUntil) return;
    const delay = Date.parse(value.validUntil) - Date.now();
    if (delay <= 0) {
      stale.value = true;
      return;
    }
    timer = setTimeout(
      () => expireAtBoundary(value),
      Math.min(delay, 2147483647),
    );
  }
  async function preview(): Promise<void> {
    if (!canPreview.value) return;
    cancel();
    const captured = signature.value,
      run = sequence,
      requestController = new AbortController();
    controller = requestController;
    pending.value = true;
    error.value = undefined;
    try {
      const definition = draftDefinition(
        { fields: [cloneSchemaValue(field.value!)] },
        schemaMetadata.value!,
      );
      const value = await feedCalculationApi.preview(
        {
          feedId: feedId.value,
          expectedVersion: version.value!,
          field: definition.fields[0]!,
          itemId: root.value!.id,
          variantId: root.value!.kind === "variable" ? variant.value!.id : null,
        },
        requestController.signal,
      );
      if (
        run !== sequence ||
        captured !== signature.value ||
        requestController.signal.aborted
      )
        return;
      result.value = value;
      stale.value = false;
      expireAtBoundary(value);
    } catch (failure: unknown) {
      if (
        run === sequence &&
        captured === signature.value &&
        !requestController.signal.aborted
      )
        error.value = failure;
    } finally {
      if (run === sequence) pending.value = false;
    }
  }
  function resume(): void {
    if (
      typeof document === "undefined" ||
      document.visibilityState === "visible"
    ) {
      cancel();
      stale.value = !!result.value;
    }
  }
  onMounted(() => {
    if (typeof window !== "undefined") {
      window.addEventListener("focus", resume);
      document.addEventListener("visibilitychange", resume);
    }
  });
  onScopeDispose(() => {
    cancel();
    if (typeof window !== "undefined") {
      window.removeEventListener("focus", resume);
      document.removeEventListener("visibilitychange", resume);
    }
  });
  return {
    metadata,
    locale,
    products,
    variants,
    search,
    offset,
    variantOffset,
    root,
    variant,
    result,
    error,
    pending,
    stale,
    canPreview,
    preview,
  };
}
