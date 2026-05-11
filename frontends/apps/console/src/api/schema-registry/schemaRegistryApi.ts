import {httpClient} from "@/api/http/httpClient";
import type {
    CreateCustomFieldPayload,
    CreateCustomObjectPayload,
    DeleteFieldPayload,
    DeleteObjectPayload,
    ListObjectsResponse,
    RuntimeField,
    RuntimeFieldOption,
    RuntimeObject
} from "@/api/schema-registry/types";

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
    },

    createObject: async (payload: CreateCustomObjectPayload): Promise<RuntimeObject> => {
        const response = await httpClient.post<RuntimeObjectResponse>("/config/objects/create", payload);

        return normalizeObject(response.data);
    },

    deleteObject: async (objectId: string): Promise<void> => {
        const payload: DeleteObjectPayload = {
            object_id: objectId
        };

        await httpClient.delete("/config/objects/delete", {
            data: payload
        });
    },

    createField: async (objectId: string, field: CreateCustomFieldPayload["field"]): Promise<RuntimeObject> => {
        const payload: CreateCustomFieldPayload = {
            object_id: objectId,
            field
        };
        const response = await httpClient.post<RuntimeObjectResponse>("/config/objects/fields/create", payload);

        return normalizeObject(response.data);
    },

    deleteField: async (objectId: string, fieldId: string): Promise<RuntimeObject> => {
        const payload: DeleteFieldPayload = {
            object_id: objectId,
            field_id: fieldId
        };
        const response = await httpClient.delete<RuntimeObjectResponse>("/config/objects/fields/delete", {
            data: payload
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
