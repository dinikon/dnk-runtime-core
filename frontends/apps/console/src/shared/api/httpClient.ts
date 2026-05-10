import {apiBaseUrl} from "@/shared/config/env";

type RequestOptions = Omit<RequestInit, "body"> & {
    body?: unknown;
};

export class HttpError extends Error {
    constructor(
        public readonly status: number,
        public readonly path: string,
        public readonly detail?: unknown
    ) {
        super(`HTTP ${status} for ${path}`);
    }
}

async function request<TResponse>(path: string, options: RequestOptions = {}): Promise<TResponse> {
    const {body, headers, ...requestInit} = options;
    const requestHeaders = new Headers(headers);

    if (body !== undefined && !requestHeaders.has("Content-Type")) {
        requestHeaders.set("Content-Type", "application/json");
    }

    const response = await fetch(`${apiBaseUrl}${path}`, {
        credentials: "include",
        ...requestInit,
        headers: requestHeaders,
        body: body === undefined ? undefined : JSON.stringify(body)
    });

    if (!response.ok) {
        let detail: unknown;

        try {
            detail = await response.json();
        } catch {
            detail = await response.text();
        }

        throw new HttpError(response.status, path, detail);
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
