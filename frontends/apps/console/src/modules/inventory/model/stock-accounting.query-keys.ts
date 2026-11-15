import type { InventoryScope } from "./inventory-scope.types";
import type {
  StockReadParams,
  StockBalancesParams,
} from "./stock-accounting.types";
export const stockAccountingKeys = {
  listStockBalances: (scope: InventoryScope, value: StockBalancesParams) =>
    [
      "inventory",
      ...scope,
      "accounting",
      "list_stock_balances",
      { ...value, filters: { ...value.filters } },
    ] as const,
  root: (scope: InventoryScope) =>
    ["inventory", ...scope, "accounting"] as const,
  listStockPositions: (scope: InventoryScope, value: StockReadParams) =>
    [
      "inventory",
      ...scope,
      "accounting",
      "list_stock_positions",
      { ...value, filters: { ...value.filters } },
    ] as const,
  getStockPosition: (scope: InventoryScope, value: string) =>
    ["inventory", ...scope, "accounting", "get_stock_position", value] as const,
  listStockMovements: (scope: InventoryScope, value: StockReadParams) =>
    [
      "inventory",
      ...scope,
      "accounting",
      "list_stock_movements",
      { ...value, filters: { ...value.filters } },
    ] as const,
  listStockExecutions: (scope: InventoryScope, value: StockReadParams) =>
    [
      "inventory",
      ...scope,
      "accounting",
      "list_stock_executions",
      { ...value, filters: { ...value.filters } },
    ] as const,
  listStockPostings: (scope: InventoryScope, value: StockReadParams) =>
    [
      "inventory",
      ...scope,
      "accounting",
      "list_stock_postings",
      { ...value, filters: { ...value.filters } },
    ] as const,
  getStockExecutionDetails: (scope: InventoryScope, value: string) =>
    [
      "inventory",
      ...scope,
      "accounting",
      "get_stock_execution_details",
      value,
    ] as const,
  getStockPostingDetails: (scope: InventoryScope, value: string) =>
    [
      "inventory",
      ...scope,
      "accounting",
      "get_stock_posting_details",
      value,
    ] as const,
};
