export interface CreateContactPayload {
  first_name: string;
  last_name?: string | null;
  middle_name?: string | null;
  status?: string | null;
  tags?: string[];
}

export interface UpdateContactPayload {
  first_name: string;
  last_name?: string | null;
  middle_name?: string | null;
  status?: string | null;
  tags?: string[] | null;
}

export interface CreateCompanyPayload {
  legal_name: string;
}

export interface UpdateCompanyPayload {
  legal_name: string;
}
