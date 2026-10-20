export type PublicationIdentityState =
  "missing" | "duplicate" | "valid" | "not_required";
export interface PublicationIdentity {
  state: PublicationIdentityState;
  key: string | null;
  conflictCount: number;
}
export interface PublicationIdentitySummary {
  label: string;
  total: number;
  missing: number;
  duplicate: number;
  valid: number;
  duplicateGroups: number;
  assessment:
    "not_started" | "in_progress" | "current" | "stale" | "incomplete";
  checkedAt: string | null;
  scopeLimitations: string[];
  helpTitle: string;
  helpSteps: string[];
  helpUrl: string;
  recoveryVerified: boolean;
}
