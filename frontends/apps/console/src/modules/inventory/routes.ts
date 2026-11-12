import type { RouteRecordRaw } from "vue-router";

export const inventoryRoutes: RouteRecordRaw[] = [
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
