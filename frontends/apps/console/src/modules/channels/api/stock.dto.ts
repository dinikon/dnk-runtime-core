export interface StockOperationDto {
  publication_id: string;
  operation_id: string;
  direction: "read" | "write";
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  quantity: string | null;
  availability: string | null;
  observed_at: string | null;
  desired_quantity: number | null;
  error_code: string | null;
  updated_at: string;
  recovery_required: boolean;
}
export interface BindingStockDto {
  allow_stock_export: boolean;
  items: {
    publication_id: string;
    stock_owner_id: string;
    catalog_position_id: string;
    catalog_owner_id: string;
    catalog_quantity: number | null;
    publication_quantity: string | null;
    publication_availability: string | null;
    export_blocker: string | null;
    operation: StockOperationDto | null;
  }[];
}
export interface RefreshPublicationStockRequestDto {
  publication_ids: string[];
}
export interface ExportCatalogStockRequestDto {
  publication_ids: string[];
}
export interface RefreshPublicationStockResponseDto {
  operation_ids: string[];
}
export interface ExportCatalogStockResponseDto {
  operation_ids: string[];
}
