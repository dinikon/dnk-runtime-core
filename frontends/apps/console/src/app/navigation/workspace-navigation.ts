import {
  Building2,
  FileSpreadsheet,
  LifeBuoy,
  ShoppingBasket,
  Users,
} from "@lucide/vue";

import type { WorkspaceNavigation } from "./workspace-navigation.types";

export const workspaceNavigation: WorkspaceNavigation = {
  navGroups: [
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
