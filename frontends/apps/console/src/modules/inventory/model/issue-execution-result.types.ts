export interface IssueExecutionResult {
  documentId: string;
  executionId: string;
  postingId: string;
  versionBefore: number;
  versionAfter: number;
  documentStatus: string;
  lines: {
    id: string;
    sku: string;
    sourceQuantity: string;
    sourceUom: string;
    quantity: string;
    baseUom: string;
    locationCode: string;
    lotNumber: string | null;
    serialNumber: string | null;
    positionId: string;
  }[];
  positions: {
    id: string;
    baseUom: string;
    before: string;
    delta: string;
    after: string;
    beforeVersion: number;
    afterVersion: number;
  }[];
}
