import {httpClient} from "@/api/http/httpClient";
import type {RuntimeObject} from "@/api/schema-registry";
import type {
    ListObjectRecordsParams,
    ListObjectRecordsResponse,
    ObjectRecord
} from "@/api/object-records/types";

interface StandardRecordListResponse {
    items: Array<Record<string, unknown> & { id: string }>;
    limit: number;
    offset: number;
    count: number;
}

interface CustomRecordResponse {
    object_id: string;
    row_id: string;
    values: Record<string, unknown>;
}

interface CustomRecordListResponse {
    items: CustomRecordResponse[];
    limit: number;
    offset: number;
    count: number;
}

const STANDARD_OBJECT_ENDPOINTS: Record<string, string> = {
    contacts: "/crm/contacts",
    products: "/inventory/products",
    product_categories: "/inventory/categories"
};

export class ObjectRecordsAdapterNotFoundError extends Error {
    constructor(objectName: string) {
        super(`Data endpoint is not configured for '${objectName}'.`);
        this.name = "ObjectRecordsAdapterNotFoundError";
    }
}

export const objectRecordsApi = {
    list: async (
        object: RuntimeObject,
        params: ListObjectRecordsParams = {}
    ): Promise<ListObjectRecordsResponse> => {
        const limit = params.limit ?? 50;
        const offset = params.offset ?? 0;

        if (object.kind.trim().toLowerCase() === "custom") {
            return listCustomObjectRecords(object.id, limit, offset);
        }

        const endpoint = STANDARD_OBJECT_ENDPOINTS[object.plural_name];
        if (!endpoint) {
            throw new ObjectRecordsAdapterNotFoundError(object.plural_name);
        }

        return listStandardObjectRecords(endpoint, limit, offset);
    }
};

export function isObjectRecordsAdapterNotFoundError(
    error: unknown
): error is ObjectRecordsAdapterNotFoundError {
    return error instanceof ObjectRecordsAdapterNotFoundError;
}

async function listStandardObjectRecords(
    endpoint: string,
    limit: number,
    offset: number
): Promise<ListObjectRecordsResponse> {
    const response = await httpClient.get<StandardRecordListResponse>(endpoint, {
        params: {
            limit,
            offset
        }
    });

    return {
        items: response.data.items.map((item) => ({
            id: item.id,
            values: {...item}
        })),
        limit: response.data.limit,
        offset: response.data.offset,
        count: response.data.count
    };
}

async function listCustomObjectRecords(
    objectId: string,
    limit: number,
    offset: number
): Promise<ListObjectRecordsResponse> {
    const response = await httpClient.post<CustomRecordListResponse>("/custom-objects/records/list", {
        object_id: objectId,
        limit,
        offset
    });

    return {
        items: response.data.items.map(customRecordToObjectRecord),
        limit: response.data.limit,
        offset: response.data.offset,
        count: response.data.count
    };
}

function customRecordToObjectRecord(record: CustomRecordResponse): ObjectRecord {
    return {
        id: record.row_id,
        values: {...record.values}
    };
}
