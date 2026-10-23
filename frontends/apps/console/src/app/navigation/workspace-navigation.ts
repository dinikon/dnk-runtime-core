import {
  Building2,
  LifeBuoy,
  ShoppingBasket,
  Users,
} from "@lucide/vue";

import type { WorkspaceNavigation } from "./workspace-navigation.types";

export const workspaceNavigation: WorkspaceNavigation = {
  navGroups: [
    {
      title: "Каталог",
      items: [{ title: "Товары", url: "/catalog/items", icon: ShoppingBasket }],
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
  ],
  support: {
    title: "Support",
    url: "https://t.me/iNikon",
    icon: LifeBuoy,
    external: true,
  },
};
