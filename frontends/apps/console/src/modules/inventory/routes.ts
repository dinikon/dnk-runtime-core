import type { RouteRecordRaw } from "vue-router";

export const inventoryRoutes: RouteRecordRaw[] = [
  {
    path: "inventory/stock-documents/internal-moves",
    name: "inventory-internal-move-documents",
    component: () => import("./pages/InternalMoveDocumentsPage.vue"),
  },
  {
    path: "inventory/stock-documents/internal-moves/new",
    name: "inventory-internal-move-create",
    component: () => import("./pages/CreateInternalMoveDraftPage.vue"),
  },
  {
    path: "inventory/stock-documents/internal-moves/:documentId/move",
    name: "inventory-internal-move-execute",
    component: () => import("./pages/InternalMoveStockDocumentPage.vue"),
  },
  {
    path: "inventory/stock-documents/internal-moves/:documentId",
    name: "inventory-internal-move-document",
    component: () => import("./pages/InternalMoveDocumentPage.vue"),
  },
  {
    path: "inventory/stock-documents/issues",
    name: "inventory-issue-documents",
    component: () => import("./pages/IssueDocumentsPage.vue"),
  },
  {
    path: "inventory/stock-documents/issues/new",
    name: "inventory-issue-create",
    component: () => import("./pages/CreateIssueDraftPage.vue"),
  },
  {
    path: "inventory/stock-documents/issues/:documentId/issue",
    name: "inventory-issue-execute",
    component: () => import("./pages/IssueStockDocumentPage.vue"),
  },
  {
    path: "inventory/stock-documents/issues/:documentId",
    name: "inventory-issue-document",
    component: () => import("./pages/IssueDocumentPage.vue"),
  },
  {
    path: "/inventory/stock-positions",
    name: "inventory-stock-positions",
    component: () => import("./pages/StockAccountingPage.vue"),
    props: { kind: "positions" },
  },
  {
    path: "/inventory/stock-movements",
    name: "inventory-stock-movements",
    component: () => import("./pages/StockAccountingPage.vue"),
    props: { kind: "movements" },
  },
  {
    path: "/inventory/stock-executions",
    name: "inventory-stock-executions",
    component: () => import("./pages/StockAccountingPage.vue"),
    props: { kind: "executions" },
  },
  {
    path: "/inventory/stock-postings",
    name: "inventory-stock-postings",
    component: () => import("./pages/StockAccountingPage.vue"),
    props: { kind: "postings" },
  },
  {
    path: "/inventory/stock-positions/:positionId",
    name: "inventory-stock-position",
    component: () => import("./pages/StockPositionPage.vue"),
  },
  {
    path: "/inventory/stock-documents/:documentId/receive",
    name: "inventory-receipt-receive",
    component: () => import("./pages/ReceiveStockDocumentPage.vue"),
  },
  {
    path: "/inventory/stock-executions/:identifier",
    name: "inventory-stock-execution",
    component: () => import("./pages/StockReceiptFactPage.vue"),
    props: { kind: "execution" },
  },
  {
    path: "/inventory/stock-postings/:identifier",
    name: "inventory-stock-posting",
    component: () => import("./pages/StockReceiptFactPage.vue"),
    props: { kind: "posting" },
  },
  {
    path: "inventory/stock-documents",
    name: "inventory-receipt-documents",
    component: () => import("./pages/ReceiptDocumentsPage.vue"),
  },
  {
    path: "inventory/stock-documents/new",
    name: "inventory-receipt-create",
    component: () => import("./pages/CreateReceiptDraftPage.vue"),
  },
  {
    path: "inventory/stock-documents/:documentId",
    name: "inventory-receipt-document",
    component: () => import("./pages/ReceiptDocumentPage.vue"),
  },
  {
    path: "inventory/items/:inventoryItemId/serials/:serialId",
    name: "inventory-stock-serial",
    component: () => import("./pages/StockSerialPage.vue"),
  },
  {
    path: "inventory/items/:inventoryItemId/serials",
    name: "inventory-stock-serials",
    component: () => import("./pages/StockSerialsPage.vue"),
  },
  {
    path: "inventory/items/:inventoryItemId/lots/:lotId",
    name: "inventory-stock-lot",
    component: () => import("./pages/StockLotPage.vue"),
  },
  {
    path: "inventory/items/:inventoryItemId/lots",
    name: "inventory-stock-lots",
    component: () => import("./pages/StockLotsPage.vue"),
  },
  {
    path: "inventory/items/:inventoryItemId/packagings/:packagingId",
    name: "inventory-item-packaging-edit",
    component: () => import("./pages/ItemPackagingEditPage.vue"),
  },
  {
    path: "inventory/items/:inventoryItemId/packagings",
    name: "inventory-item-packagings",
    component: () => import("./pages/ItemPackagingsPage.vue"),
  },
  {
    path: "inventory/packaging-types/:packagingTypeId",
    name: "inventory-packaging-type-edit",
    component: () => import("./pages/PackagingTypeEditPage.vue"),
  },
  {
    path: "inventory/packaging-types",
    name: "inventory-packaging-types",
    component: () => import("./pages/PackagingTypesPage.vue"),
  },
  {
    path: "inventory/warehouses/:warehouseId/locations/:locationId",
    name: "inventory-stock-location-edit",
    component: () => import("./pages/StockLocationEditPage.vue"),
  },
  {
    path: "inventory/warehouses/:warehouseId/locations",
    name: "inventory-stock-locations",
    component: () => import("./pages/StockLocationsPage.vue"),
  },
  {
    path: "inventory/warehouses/:warehouseId",
    name: "inventory-warehouse-edit",
    component: () => import("./pages/WarehouseEditPage.vue"),
  },
  {
    path: "inventory/warehouses",
    name: "inventory-warehouses",
    component: () => import("./pages/WarehousesPage.vue"),
  },
  {
    path: "inventory/items/:inventoryItemId",
    name: "inventory-item-edit",
    component: () => import("./pages/InventoryItemEditPage.vue"),
  },
  {
    path: "inventory/items",
    name: "inventory-items",
    component: () => import("./pages/InventoryItemsPage.vue"),
  },
];
