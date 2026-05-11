export interface Contact {
    id: string;
    created_at: string;
    updated_at: string;
    last_name: string | null;
    first_name: string;
    middle_name: string | null;
    status: string | null;
    tags: string[];
}

export interface ListContactsResponse {
    items: Contact[];
    limit: number;
    offset: number;
    count: number;
}
