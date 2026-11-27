import { computed, onScopeDispose, shallowRef, watch, type ComputedRef, type Ref, type ShallowRef } from "vue";
import { feedAccessApi } from "../api/feed-access.api";
import { useFeedAccessTokens } from "./feed-access.queries";
import { useFeedAction } from "./use-feed-action";
import { useFeedScope } from "./use-feed-scope";
import type {
  ChangedFeedAccessMode, FeedAccessMode, IssuedFeedAccessToken, IssueFeedAccessToken,
} from "./feed-access.types";

interface FeedAccessEditor {
  tokens: ReturnType<typeof useFeedAccessTokens>;
  issued: ShallowRef<IssuedFeedAccessToken | undefined>;
  pending: ComputedRef<boolean>;
  error: ComputedRef<unknown>;
  change(mode: FeedAccessMode, version: number): Promise<ChangedFeedAccessMode | undefined>;
  issue(input: IssueFeedAccessToken): Promise<void>;
  revoke(tokenId: string): Promise<void>;
  dismiss(): void;
}

export function useFeedAccessEditor(feedId: Ref<string>, canManage: Ref<boolean>): FeedAccessEditor {
  const scope = useFeedScope();
  const context = computed(() => JSON.stringify([scope.value, feedId.value, canManage.value]));
  const tokens = useFeedAccessTokens(feedId, canManage);
  const changeAction = useFeedAction(
    (input: { version: number; mode: FeedAccessMode }, signal) =>
      feedAccessApi.change(feedId.value, input.version, input.mode, signal),
    context,
  );
  const issueAction = useFeedAction(
    (input: IssueFeedAccessToken, signal) => feedAccessApi.issue(feedId.value, input, signal),
    context,
  );
  const revokeAction = useFeedAction(
    (tokenId: string, signal) => feedAccessApi.revoke(feedId.value, tokenId, signal),
    context,
  );
  const issued = shallowRef<IssuedFeedAccessToken>();
  const pending = computed(() =>
    changeAction.pending.value || issueAction.pending.value || revokeAction.pending.value,
  );
  const error = computed(() =>
    changeAction.error.value || issueAction.error.value || revokeAction.error.value,
  );
  function dismiss(): void {
    issued.value = undefined;
  }
  watch(context, dismiss, { flush: "sync" });
  onScopeDispose(dismiss);

  function ready(): boolean {
    if (!canManage.value || pending.value) return false;
    changeAction.error.value = undefined;
    issueAction.error.value = undefined;
    revokeAction.error.value = undefined;
    return true;
  }
  async function change(mode: FeedAccessMode, version: number): Promise<ChangedFeedAccessMode | undefined> {
    if (ready()) return (await changeAction.execute({ mode, version }))?.value;
  }
  async function issue(input: IssueFeedAccessToken): Promise<void> {
    if (issued.value || !ready()) return;
    const current = context.value;
    const result = await issueAction.execute(input);
    if (!result || context.value !== current) return;
    // The secret lives only in this editor, outside the query cache.
    issued.value = result.value;
    await tokens.refetch();
  }
  async function revoke(tokenId: string): Promise<void> {
    if (!ready()) return;
    const current = context.value;
    const result = await revokeAction.execute(tokenId);
    if (!result || context.value !== current) return;
    if (issued.value?.id === tokenId) dismiss();
    await tokens.refetch();
  }
  return { tokens, issued, pending, error, change, issue, revoke, dismiss };
}
