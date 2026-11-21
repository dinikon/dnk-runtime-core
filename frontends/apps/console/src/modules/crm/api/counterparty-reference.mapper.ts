import type { SearchCounterpartyReferencesResponseDTO } from "./counterparty-reference.dto";
import type { CounterpartyReferencesPage } from "../model/counterparty-reference.types";
export function counterpartyReferencesFromDto(
  dto: SearchCounterpartyReferencesResponseDTO,
): CounterpartyReferencesPage {
  return {
    ...dto,
    items: dto.items.map((item) => ({
      id: item.id,
      modelKey: item.model_key,
      name: item.display_name,
    })),
  };
}
