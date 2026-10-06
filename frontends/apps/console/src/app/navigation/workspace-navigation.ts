import {
  Building2,
  Package,
  Warehouse,
  FileSpreadsheet,
  LifeBuoy,
  ShoppingBasket,
  Users,
} from "@lucide/vue";

import type { WorkspaceNavigation } from "./workspace-navigation.types";

export const workspaceNavigation: WorkspaceNavigation = {
  navGroups: [
    {
      title: "Склад",
      items: [{ title: "SKU", url: "/inventory/skus", icon: Warehouse }],
    },
    {
      title: "Каталог",
      items: [
        { title: "Товары", url: "/catalog/products", icon: Package },
        { title: "Категории", url: "/catalog/categories", icon: Package },
        { title: "Типы товаров", url: "/catalog/product-types", icon: Package },
        { title: "Контент-блоки", url: "/catalog/content-blocks", icon: Package },
      ],
    },
    {
      title: "CRM",
      items: [
        {
          title: "Контакты",
          url: "/crm/contacts",
          icon: Users,
          defaultOpen: true,
          items: [
            {
              title: "Контакты",
              url: "/crm/contacts",
              icon: Users,
            },
            {
              title: "Компании",
              url: "/crm/companies",
              icon: Building2,
            },
          ],
        },
      ],
    },
    {
      title: "Закупки",
      items: [
        {
          title: "Прайс-листы",
          url: "/purchases/price-lists",
          icon: FileSpreadsheet,
        },
        {
          title: "Офферы поставщиков",
          url: "/purchases/offers",
          icon: ShoppingBasket,
        },
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
