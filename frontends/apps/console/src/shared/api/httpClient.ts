import {apiBaseUrl} from "@/shared/config/env";

type RequestOptions = Omit<RequestInit, "body"> & {
    body?: unknown;
};

async function request<TResponse>(path: string, options: RequestOptions = {}): Promise<TResponse> {
    const {body, headers, ...requestInit} = options;
    const response = await fetch(`${apiBaseUrl}${path}`, {
        credentials: "include",
        ...requestInit,
        headers: {
            "Content-Type": "application/json",
            ...headers
        },
        body: body === undefined ? undefined : JSON.stringify(body)
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status} for ${path}`);
    }

    if (response.status === 204) {
        return undefined as TResponse;
    }

    return response.json() as Promise<TResponse>;
}

export const httpClient = {
    get: <TResponse>(path: string, options?: RequestOptions) =>
        request<TResponse>(path, {...options, method: "GET"}),
    post: <TResponse>(path: string, body?: unknown, options?: RequestOptions) =>
        request<TResponse>(path, {...options, method: "POST", body}),
    patch: <TResponse>(path: string, body?: unknown, options?: RequestOptions) =>
        request<TResponse>(path, {...options, method: "PATCH", body})
};
