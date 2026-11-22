import {
  onScopeDispose,
  ref,
  shallowRef,
  watch,
  type Ref,
  type ShallowRef,
} from "vue";
import { feedPreviewApi } from "../api/feed-preview.api";
import { FeedRequestGuard } from "./feed.request-guard";
import type { FeedPreviewRequest } from "./feed-preview.types";
import { useFeedScope } from "./use-feed-scope";

interface TestCsvDownload {
  pending: Ref<boolean>;
  error: ShallowRef<unknown>;
  execute(input: FeedPreviewRequest): Promise<Blob | undefined>;
}

export function useDownloadTestCsv(
  id: Ref<string>,
  version: Ref<number | null>,
): TestCsvDownload {
  const scope = useFeedScope();
  const pending = ref(false);
  const error = shallowRef<unknown>();
  const guard = new FeedRequestGuard();
  watch(
    [scope, id, version],
    () => {
      guard.cancel();
      pending.value = false;
      error.value = undefined;
    },
    { flush: "sync" },
  );
  onScopeDispose(() => guard.dispose());

  async function execute(input: FeedPreviewRequest): Promise<Blob | undefined> {
    if (!scope.value[0] || !scope.value[1]) return;
    const request = guard.start();
    if (!request) return;
    pending.value = true;
    error.value = undefined;
    try {
      const result = await feedPreviewApi.download(input, request.signal);
      if (guard.current(request)) return result;
    } catch (reason: unknown) {
      if (guard.current(request)) error.value = reason;
    } finally {
      if (guard.current(request)) {
        guard.finish(request);
        pending.value = false;
      }
    }
  }

  return { pending, error, execute };
}
