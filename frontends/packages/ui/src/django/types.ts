export interface FieldSchema {
  type: string;
  attrs: Record<string, string | boolean | number>;
  label: string;
  value: string | boolean | number;
  help: string;
  errors: string[];
  options: { value: string; label: string }[];
  checked?: boolean;
  checkboxValue?: string;
}

declare global {
  interface Window {
    coreUIState?: "pending" | "ready" | "fallback";
    coreUIReady?: Promise<void>;
    resolveCoreUI?: () => void;
  }
}
