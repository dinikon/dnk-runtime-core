import type { DataTableColumn } from "@/components/custom-ui/data-table";
export type CompaniesExampleColumn =
  | "selection"
  | "name"
  | "domain"
  | "creator"
  | "address"
  | "owner"
  | "icp"
  | "arr"
  | "linkedin";
export const companiesExampleColumns: readonly DataTableColumn<CompaniesExampleColumn>[] =
  [
    {
      key: "selection",
      label: "Select",
      width: 40,
      pinned: "start",
      align: "center",
    },
    { key: "name", label: "Companies", width: 200, pinned: "start" },
    { key: "domain", label: "Url", width: 180 },
    { key: "creator", label: "Created By", width: 195 },
  { key: "address", label: "Address", width: 205, grow: true },
    { key: "owner", label: "Account Owner", width: 190 },
    { key: "icp", label: "ICP", width: 105 },
    { key: "arr", label: "ARR", width: 145, align: "right" },
    { key: "linkedin", label: "LinkedIn", width: 165 },
  ];
