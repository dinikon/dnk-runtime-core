export class HttpError extends Error {
    constructor(
        public readonly status: number,
        public readonly path: string,
        public readonly detail?: unknown
    ) {
        super(`HTTP ${status} for ${path}`);
    }
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
    if (!(error instanceof HttpError)) {
        return fallback;
    }

    if (typeof error.detail === "string" && error.detail.trim().length > 0) {
        return error.detail;
    }

    if (
        error.detail &&
        typeof error.detail === "object" &&
        "detail" in error.detail &&
        typeof error.detail.detail === "string"
    ) {
        return error.detail.detail;
    }

    return fallback;
}
