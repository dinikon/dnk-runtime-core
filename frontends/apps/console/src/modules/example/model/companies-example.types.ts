export interface ExampleCompany {
  id: string;
  name: string;
  domain: string;
  creator: string;
  address: string;
  owner: string;
  icp: boolean;
  arr: number;
  linkedin: string;
}

export interface CompaniesExampleParams {
  search: string;
  icp: "all" | "true" | "false";
  sort: "original" | "name" | "arr-desc";
}
