import type {
  CounterpartyReferenceScope,
  CounterpartyReferencesParams,
} from "./counterparty-reference.types";
export const counterpartyReferenceKeys = {
  list: (
    scope: CounterpartyReferenceScope,
    params: CounterpartyReferencesParams,
  ) => ["crm-counterparty-references", ...scope, { ...params }] as const,
};
