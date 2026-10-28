export type BindingMode =
  "SIMPLE_TO_SIMPLE" | "VARIABLE_TO_VARIABLE" | "VARIABLE_TO_SIMPLE";
export interface BindingPair {
  catalogId: string;
  publicationId: string;
}
export interface BindingPosition {
  id: string;
  kind: string;
  title: string | null;
  sku: string | null;
  imageUrl: string | null;
  status: string | null;
  price: string | null;
  currency: string | null;
  quantity: string | null;
  availability: string | null;
  stockSourceId: string;
  externalId: string | null;
  stale: boolean;
}
export interface BindingPreview {
  catalogRoot: BindingPosition | null;
  catalogPositions: BindingPosition[];
  publications: BindingPosition[];
  state: "linked" | "partial" | "conflict";
  issues: string[];
  catalogCount: number;
  publicationCount: number;
  matchedCount: number;
  catalogToken: string;
  publicationToken: string;
  suggestions: BindingPair[];
}
export interface CatalogBinding {
  id: string;
  channelId: string;
  channelName: string;
  platform: string;
  catalogRootId: string;
  mode: BindingMode;
  publicationRootId: string | null;
  revision: number;
  items: BindingPair[];
  preview: BindingPreview;
  updatedAt: string;
}
export interface BindingPage {
  items: CatalogBinding[];
  total: number;
  offset: number;
  limit: number;
}
export interface BindingCandidates {
  items: BindingPosition[];
  occupiedIds: string[];
  total: number;
  offset: number;
  limit: number;
}
export interface BindingProposal {
  catalogRootId: string;
  mode: BindingMode;
  publicationRootId: string | null;
  items: BindingPair[];
  locale: string;
  groupId?: string;
}
export interface BindingFilters {
  mode?: BindingMode;
  catalogRootId?: string;
  channelId?: string;
  publicationId?: string;
  locale: string;
  offset: number;
  limit: number;
}
export interface BindingCandidateFilters {
  channelId: string;
  mode: BindingMode;
  locale: string;
  search: string;
  offset: number;
  limit: number;
}
export const bindingModes: Record<BindingMode, string> = {
  SIMPLE_TO_SIMPLE: "Простой → простой",
  VARIABLE_TO_VARIABLE: "Вариативный → вариативный",
  VARIABLE_TO_SIMPLE: "Варианты → самостоятельные товары",
};
export const bindingStates: Record<string, string> = {
  linked: "Связана",
  partial: "Частичная",
  conflict: "Требует проверки",
};
