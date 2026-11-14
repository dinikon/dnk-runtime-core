export type CounterpartyModelKey = "crm.company" | "crm.contact";
export interface CounterpartyReference {
  modelKey: CounterpartyModelKey;
  id: string;
  name: string;
}
export interface CounterpartyReferencesPage {
  items: CounterpartyReference[];
  total: number;
  offset: number;
  limit: number;
}
export interface CounterpartyReferencesParams {
  model_key: CounterpartyModelKey;
  search: string;
  offset: number;
  limit: number;
}
export type CounterpartyReferenceScope = readonly [
  string | null,
  string | null,
  string,
];
