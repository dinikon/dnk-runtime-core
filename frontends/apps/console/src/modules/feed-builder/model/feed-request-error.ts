import { FeedApiError } from "./feed.types.ts";

export interface FeedRequestIssue {
  code: string;
  message: string;
  fieldId?: string;
  path: (string | number)[];
}
export class FeedRequestError extends FeedApiError {
  readonly issues: FeedRequestIssue[];
  constructor(status: number | undefined, issues: FeedRequestIssue[]) {
    super(status);
    this.issues = issues;
  }
}
