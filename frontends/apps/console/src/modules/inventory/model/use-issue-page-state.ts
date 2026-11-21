import { computed, type ComputedRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import { parseIssuePage, issuePageQuery } from "./issue-page-state";
import type { IssuesParams } from "./issue.types";
export interface IssuePageState {
  params: ComputedRef<IssuesParams>;
  change(v: Partial<IssuesParams>): void;
  page(offset: number): void;
}
export function useIssuePageState(): IssuePageState {
  const route = useRoute(),
    router = useRouter(),
    params = computed(() => parseIssuePage(route.query));
  const replace = (v: IssuesParams): void => {
    void router.replace({ query: issuePageQuery(v) });
  };
  return {
    params,
    change: (v) => replace({ ...params.value, ...v, offset: 0 }),
    page: (offset) => replace({ ...params.value, offset }),
  };
}
