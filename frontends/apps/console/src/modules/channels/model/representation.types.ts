import type { BindingMode } from "./bindings/binding.types";

export interface RepresentationFieldOrigin {
  kind: "catalog" | "catalog_parent" | "missing";
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
}
