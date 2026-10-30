import type { BindingMode } from "./bindings/binding.types";

export interface RepresentationFieldOrigin {
  kind:
    | "catalog"
    | "catalog_parent"
    | "missing"
    | "group_override"
    | "item_override";
  catalogPositionId: string | null;
}
export interface RepresentationContent {
  locale: string;
  title: string | null;
  body: string | null;
  gallery: { fileId: string; alt: string; caption: string }[] | null;
  origins: {
    title: RepresentationFieldOrigin;
    body: RepresentationFieldOrigin;
    gallery: RepresentationFieldOrigin;
  };
}
export interface RepresentationIssue {
  code: string;
  publicationId: string | null;
  field: string | null;
  locale: string | null;
}
export interface RepresentationTarget {
  publicationId: string;
  externalId: string | null;
  parentPublicationId: string | null;
  publicationKind: string | null;
  bindingItemId: string | null;
  catalogPositionId: string;
  role: "container" | "position";
  content: RepresentationContent[];
  catalogContent: RepresentationContent[];
  ready: boolean;
  issues: RepresentationIssue[];
}
export interface RepresentationPreview {
  channelId: string;
  connectionId: string;
  bindingGroupId: string;
  bindingRevision: number;
  configRevision: number;
  platform: string;
  mode: BindingMode;
  locales: string[];
  asOf: string;
  bindingState: "linked" | "partial" | "conflict";
  issues: RepresentationIssue[];
  targets: RepresentationTarget[];
  exportBlockers: string[];
  draft: boolean;
}

export interface RepresentationImage {
  fileId: string;
  alt: string;
  caption: string;
}
export interface LocalizedOverrides {
  title?: string | null;
  body?: string | null;
  gallery?: RepresentationImage[] | null;
}
export interface RepresentationOverrides {
  common: Record<string, LocalizedOverrides>;
  items: Record<string, Record<string, LocalizedOverrides>>;
}
export interface RepresentationState {
  id: string | null;
  revision: number;
  exportEnabled: boolean;
  overrides: RepresentationOverrides;
  createdAt: string | null;
  updatedAt: string | null;
  createdBy: string | null;
  updatedBy: string | null;
}
export interface RepresentationDetails {
  state: RepresentationState;
  bindingRevision: number;
  configRevision: number;
  locales: string[];
  items: { id: string; catalogPositionId: string; publicationId: string }[];
}
export interface RepresentationVersion {
  expectedRevision: number;
  expectedBindingRevision: number;
  expectedConfigRevision: number;
}
export interface RepresentationDraftInput extends RepresentationVersion {
  overrides: RepresentationOverrides;
}
export interface RepresentationWriteInput extends RepresentationVersion {
  channelId: string;
  groupId: string;
}
export interface SaveRepresentationInput extends RepresentationWriteInput {
  overrides: RepresentationOverrides;
}
