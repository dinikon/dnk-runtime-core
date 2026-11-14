import type { CounterpartyModelKey } from "../model/counterparty-reference.types";
export interface SearchCounterpartyReferencesResponseDTO {
  items: {
    id: string;
    model_key: CounterpartyModelKey;
    display_name: string;
  }[];
  total: number;
  offset: number;
  limit: number;
}
