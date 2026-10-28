import { Building2, LifeBuoy, ShoppingBasket, Users, Plug } from "@lucide/vue";

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
