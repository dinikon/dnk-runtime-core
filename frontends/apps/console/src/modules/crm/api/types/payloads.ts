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
