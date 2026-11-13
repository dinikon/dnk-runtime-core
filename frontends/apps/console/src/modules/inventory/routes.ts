import type { RouteRecordRaw } from "vue-router";

export const inventoryRoutes: RouteRecordRaw[] = [
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
