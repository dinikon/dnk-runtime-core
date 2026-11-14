import { httpClient, getApiErrorMessage } from "@/app/providers/http";
import { isCancel } from "axios";
import type { SearchCounterpartyReferencesResponseDTO } from "./counterparty-reference.dto";
import type {
  CounterpartyReferencesParams,
  CounterpartyReferencesPage,
} from "../model/counterparty-reference.types";
import { counterpartyReferencesFromDto } from "./counterparty-reference.mapper";
export async function searchCounterpartyReferences(
  params: CounterpartyReferencesParams,
  signal: AbortSignal,
): Promise<CounterpartyReferencesPage> {
  try {
    const { data } =
      await httpClient.get<SearchCounterpartyReferencesResponseDTO>(
        "/console/crm/counterparty-references",
        { params, signal },
      );
    return counterpartyReferencesFromDto(data);
  } catch (cause: unknown) {
    if (isCancel(cause)) throw cause;
    throw new Error(
      getApiErrorMessage(cause, "Не удалось найти контрагентов."),
    );
  }
}
