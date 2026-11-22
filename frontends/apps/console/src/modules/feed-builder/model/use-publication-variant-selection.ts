import {
  ref,
  shallowRef,
  watch,
  onScopeDispose,
  computed,
  type Ref,
  type ShallowRef,
} from "vue";
import { useFeedScope } from "./use-feed-scope";
import { FeedRequestGuard } from "./feed.request-guard";
import { feedPublicationApi } from "../api/feed-publication.api";
import type { PublicationChoice } from "./feed-publication.types";
export function usePublicationVariantSelection(
  feedId: Ref<string>,
  rootId: Ref<string>,
  locale: Ref<string>,
  context: Ref<string>,
): {
  pending: Ref<boolean>;
  error: ShallowRef<unknown>;
  execute(): Promise<PublicationChoice[] | undefined>;
} {
  const scope = useFeedScope(),
    pending = ref(false),
    error = shallowRef<unknown>(),
    guard = new FeedRequestGuard();
  const stamp = computed(() =>
    JSON.stringify([
      scope.value,
      feedId.value,
      rootId.value,
      locale.value,
      context.value,
    ]),
  );
  watch(
    stamp,
    () => {
      guard.cancel();
      pending.value = false;
      error.value = undefined;
    },
    { flush: "sync" },
  );
  onScopeDispose(() => guard.dispose());
  async function execute(): Promise<PublicationChoice[] | undefined> {
    if (pending.value || !scope.value[0] || !scope.value[1] || !rootId.value)
      return;
    const request = guard.start();
    if (!request) return;
    pending.value = true;
    error.value = undefined;
    try {
      const value = await feedPublicationApi.variants(
        feedId.value,
        rootId.value,
        locale.value,
        request.signal,
      );
      if (guard.current(request)) return value;
    } catch (e) {
      if (guard.current(request)) error.value = e;
    } finally {
      if (guard.current(request)) {
        pending.value = false;
        guard.finish(request);
      }
    }
    return undefined;
  }
  return { pending, error, execute };
}
