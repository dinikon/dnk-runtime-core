import {
  Building2,
  Plug,
  FileSpreadsheet,
  LifeBuoy,
  ShoppingBasket,
  Users,
} from "@lucide/vue";

import type { WorkspaceNavigation } from "./workspace-navigation.types";

export const workspaceNavigation: WorkspaceNavigation = {
  navGroups: [
    {
      title: "Каталог",
      items: [
        { title: "Товары", url: "/catalog/products", icon: ShoppingBasket },
        {
          title: "Типы контента",
          url: "/catalog/product-types",
          icon: FileSpreadsheet,
        },
        {
          title: "Блоки контента",
          url: "/catalog/content-blocks",
          icon: FileSpreadsheet,
        },
      ],
    },
    {
      title: "Интеграции",
      items: [{ title: "Каналы", url: "/channels", icon: Plug }],
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
