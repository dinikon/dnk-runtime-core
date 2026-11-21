export interface InternalMoveExecutionResult {
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
    destinationLocationId: string;
    destinationLocationCode: string;
    lotNumber: string | null;
    serialNumber: string | null;
    positionId: string;
    destinationPositionId: string;
    sourceLedgerEntryId: string;
    destinationLedgerEntryId: string;
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
