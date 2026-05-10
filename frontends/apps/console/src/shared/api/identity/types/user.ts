export interface ConsoleUserEmail {
    id: string;
    email: string;
    is_primary: boolean;
    is_verified: boolean;
}

export interface ConsoleUser {
    id: string;
    status: string;
    last_name: string;
    first_name: string;
    middle_name: string | null;
    avatar: string | null;
    interface_language: string;
    interface_theme: string;
    timezone: string;
    emails: ConsoleUserEmail[];
}
