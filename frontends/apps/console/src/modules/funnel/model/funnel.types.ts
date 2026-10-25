export interface FunnelStage {
  id: string;
  name: string;
  color: string;
  position: number;
}
export interface Funnel {
  id: string;
  modelKey: "crm.lead" | "crm.deal";
  name: string;
  isDefault: boolean;
  revision: number;
  stages: FunnelStage[];
}
export interface FunnelStageDraft {
  id?: string;
  clientKey: string;
  name: string;
  color: string;
}
export interface FunnelDraft {
  name: string;
  modelKey: "crm.lead" | "crm.deal";
  stages: FunnelStageDraft[];
}
export interface FunnelPage {
  items: Funnel[];
  total: number;
  offset: number;
  limit: number;
}
