export interface CloudStatus {
  enabled: boolean;
  linked: boolean;
}

export interface CloudStartInput {
  purpose: "login" | "link";
  silent?: boolean;
}
