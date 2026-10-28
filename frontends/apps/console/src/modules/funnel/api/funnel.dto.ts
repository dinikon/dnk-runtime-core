export interface FunnelStageDto {
  kind: "in_progress" | "won" | "lost";
  id: string;
  name: string;
  color: string;
  position: number;
}
export interface FunnelDto {
  id: string;
  model_key: "crm.lead" | "crm.deal";
  name: string;
  is_default: boolean;
  revision: number;
  stages: FunnelStageDto[];
}
export interface FunnelPageDto {
  items: FunnelDto[];
  total: number;
  offset: number;
  limit: number;
}
export interface SaveFunnelDto {
  id: string;
  revision: number;
  stage_id_map: Record<string, string>;
  moved_cards_count?: number;
}

export interface FunnelDefinitionInputDto {
  name: string;
  stages: {
    id?: string;
    client_key?: string;
    name: string;
    color: string;
    kind: "in_progress" | "won" | "lost";
  }[];
}

export interface GetFunnelDto extends Omit<FunnelDto, "stages"> {
  stages: (FunnelStageDto & { cards_count: number })[];
}
