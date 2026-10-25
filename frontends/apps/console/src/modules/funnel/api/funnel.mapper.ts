import type { FunnelDto, FunnelDefinitionInputDto } from "./funnel.dto";
import type { Funnel, FunnelDraft } from "../model/funnel.types";
export function mapFunnel(v: FunnelDto): Funnel {
  return {
    id: v.id,
    modelKey: v.model_key,
    name: v.name,
    isDefault: v.is_default,
    revision: v.revision,
    stages: v.stages.map((s) => ({ ...s })),
  };
}
export function funnelPayload(v: FunnelDraft): FunnelDefinitionInputDto {
  return {
    name: v.name,
    stages: v.stages.map((s) => ({
      ...(s.id ? { id: s.id } : { client_key: s.clientKey }),
      name: s.name,
      color: s.color,
    })),
  };
}
