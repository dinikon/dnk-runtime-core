import type { ChannelScope } from "../channel.query-keys";
import type { BindingFilters, BindingCandidateFilters } from "./binding.types";
export const bindingKeys = {
  root: (scope: ChannelScope) =>
    ["channels", ...scope, "catalog-bindings"] as const,
  list: (scope: ChannelScope, f: BindingFilters) =>
    [...bindingKeys.root(scope), "list", f] as const,
  detail: (scope: ChannelScope, channel: string, id: string, locale: string) =>
    [...bindingKeys.root(scope), "detail", channel, id, locale] as const,
  candidates: (scope: ChannelScope, kind: string, f: BindingCandidateFilters) =>
    [...bindingKeys.root(scope), "candidates", kind, f] as const,
};
