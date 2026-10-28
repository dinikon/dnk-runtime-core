export type StageKind = "in_progress" | "won" | "lost";

export interface FunnelStage {
  id: string;
  name: string;
  color: string;
  kind: StageKind;
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
  kind: StageKind;
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

export interface FunnelDetails extends Funnel {
  stages: (FunnelStage & { cardsCount: number })[];
}
export interface SaveFunnelResult {
  id: string;
  revision: number;
  stageIdMap: Record<string, string>;
  movedCardsCount: number;
}
