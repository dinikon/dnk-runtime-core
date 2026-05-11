export interface ObjectRecord {
    id: string;
    values: Record<string, unknown>;
}

export interface ListObjectRecordsParams {
    limit?: number;
    offset?: number;
}

export interface ListObjectRecordsResponse {
    items: ObjectRecord[];
    limit: number;
    offset: number;
    count: number;
}
