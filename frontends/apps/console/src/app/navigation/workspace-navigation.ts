import {
  Building2,
  LifeBuoy,
  ShoppingBasket,
  Users,
  Plug,
  Warehouse,
  Package,
} from "@lucide/vue";

import type { WorkspaceNavigation } from "./workspace-navigation.types";

export const workspaceNavigation: WorkspaceNavigation = {
  navGroups: [
    {
      title: "Каналы продаж",
      items: [{ title: "Подключения", url: "/channels", icon: Plug }],
    },
    {
      title: "Каталог",
      items: [{ title: "Товары", url: "/catalog/items", icon: ShoppingBasket }],
    },
    {
      title: "Склад",
      items: [
        {
          title: "Остатки",
          url: "/inventory/stock-positions",
          icon: Warehouse,
        },
        {
          title: "Движения",
          url: "/inventory/stock-movements",
          icon: Warehouse,
        },
        {
          title: "Поступления",
          url: "/inventory/stock-documents",
          icon: Warehouse,
        },
        {
          title: "Расходы",
          url: "/inventory/stock-documents/issues",
          icon: Warehouse,
        },
        {
          title: "Внутренние перемещения",
          url: "/inventory/stock-documents/internal-moves",
          icon: Warehouse,
        },
        { title: "Номенклатура", url: "/inventory/items", icon: Warehouse },
        { title: "Склады", url: "/inventory/warehouses", icon: Building2 },
        {
          title: "Типы тары",
          url: "/inventory/packaging-types",
          icon: Package,
        },
      ],
    },
    {
      title: "CRM",
      items: [
        { title: "Лиды", url: "/crm/leads", icon: Users },
        { title: "Сделки", url: "/crm/deals", icon: ShoppingBasket },
        { title: "Контакты", url: "/crm/contacts", icon: Users },
        { title: "Компании", url: "/crm/companies", icon: Building2 },
      ],
    },
  ],
  support: {
    title: "Support",
    url: "https://t.me/iNikon",
    icon: LifeBuoy,
    external: true,
  },
};
