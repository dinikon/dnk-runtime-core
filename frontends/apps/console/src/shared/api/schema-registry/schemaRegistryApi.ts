import {httpClient} from "@/shared/api/http/httpClient";
import type {
    ListObjectsResponse,
    RuntimeField,
    RuntimeFieldOption,
    RuntimeObject
} from "@/shared/api/schema-registry/types";

type RuntimeFieldOptionsResponse =
    | Record<string, string>
    | RuntimeFieldOption[]
    | null
    | undefined;

interface RuntimeFieldResponse extends Omit<RuntimeField, "options"> {
    options: RuntimeFieldOptionsResponse;
}

interface RuntimeObjectResponse extends Omit<RuntimeObject, "fields"> {
    fields: RuntimeFieldResponse[];
}

interface ListObjectsResponseRaw {
    items: RuntimeObjectResponse[];
    count: number;
}

export const schemaRegistryApi = {
    listObjects: async (): Promise<ListObjectsResponse> => {
        const response = await httpClient.post<ListObjectsResponseRaw>("/config/objects/list");

        return {
            items: response.data.items.map(normalizeObject),
            count: response.data.count
        };
    },

    describeObject: async (objectId: string): Promise<RuntimeObject> => {
        const response = await httpClient.post<RuntimeObjectResponse>("/config/objects/schema", {
            object_id: objectId
        });

        return normalizeObject(response.data);
    }
};

function normalizeObject(object: RuntimeObjectResponse): RuntimeObject {
    return {
        ...object,
        fields: object.fields.map(normalizeField)
    };
}

function normalizeField(field: RuntimeFieldResponse): RuntimeField {
    return {
        ...field,
        options: normalizeOptions(field.options)
    };
}

function normalizeOptions(options: RuntimeFieldOptionsResponse): RuntimeFieldOption[] {
    if (!options) {
        return [];
    }

    if (Array.isArray(options)) {
        return options;
    }

    return Object.entries(options).map(([value, label]) => ({
        value,
        label
    }));
}
