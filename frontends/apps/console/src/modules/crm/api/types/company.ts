export interface Company {
  [key: string]: unknown;
  id: string;
  created_at: string;
  updated_at: string;
  legal_name: string;
}

export interface ListCompaniesResponse {
  items: Company[];
  limit: number;
  offset: number;
  count: number;
}
