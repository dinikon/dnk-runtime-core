export interface FunnelStageDto {
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
}

export interface FunnelDefinitionInputDto {
  name: string;
  stages: { id?: string; client_key?: string; name: string; color: string }[];
}
