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
      color: s.color.toUpperCase(),
      kind: s.kind,
    })),
  };
}

export function mapFunnelDetails(
  v: import("./funnel.dto").GetFunnelDto,
): import("../model/funnel.types").FunnelDetails {
  return {
    ...mapFunnel(v),
    stages: v.stages.map(({ cards_count, ...stage }) => ({
      ...stage,
      cardsCount: cards_count,
    })),
  };
}
export function mapSaveFunnel(
  v: import("./funnel.dto").SaveFunnelDto,
): import("../model/funnel.types").SaveFunnelResult {
  return {
    id: v.id,
    revision: v.revision,
    stageIdMap: v.stage_id_map,
    movedCardsCount: v.moved_cards_count ?? 0,
  };
}
