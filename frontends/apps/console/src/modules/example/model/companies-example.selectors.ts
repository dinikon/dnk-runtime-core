import type {
  CompaniesExampleParams,
  ExampleCompany,
} from "./companies-example.types";

export function parseCompaniesExampleParams(
  query: Record<string, unknown>,
): CompaniesExampleParams {
  return {
    search: typeof query.search === "string" ? query.search : "",
    icp: query.icp === "true" || query.icp === "false" ? query.icp : "all",
    sort:
      query.sort === "name" || query.sort === "arr-desc"
        ? query.sort
        : "original",
  };
}

export function selectExampleCompanies(
  records: readonly ExampleCompany[],
  params: CompaniesExampleParams,
): ExampleCompany[] {
  const search = params.search.trim().toLocaleLowerCase();
  const rows = records.filter(
    (company) =>
      (!search ||
        `${company.name} ${company.domain}`
          .toLocaleLowerCase()
          .includes(search)) &&
      (params.icp === "all" || company.icp === (params.icp === "true")),
  );
  if (params.sort === "name")
    rows.sort((left, right) => left.name.localeCompare(right.name));
  if (params.sort === "arr-desc")
    rows.sort((left, right) => right.arr - left.arr);
  return rows;
}
