export type HeaderExampleVariant =
  | "breadcrumbs"
  | "tabs-top"
  | "search"
  | "compact"
  | "profile"
  | "tabs-bottom"
  | "search-avatar";

export interface HeaderExample {
  variant: HeaderExampleVariant;
  number: number;
  title: string;
  description?: string;
}
