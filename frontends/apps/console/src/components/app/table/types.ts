import type {Contact} from "@/shared/api/crm";

export interface ContactTableRow {
    key: string;
    contact: Contact | null;
    isDraft: boolean;
    firstName: string;
    lastName: string | null;
    middleName: string | null;
    status: string | null;
    tags: string[];
    createdAt: string | null;
    updatedAt: string | null;
}

export interface ContactTableLabels {
    name: string;
    status: string;
    tags: string;
    createdAt: string;
    updatedAt: string;
}
