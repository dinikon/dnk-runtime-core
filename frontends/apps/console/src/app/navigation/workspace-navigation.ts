import { FileSpreadsheet, LifeBuoy, ShoppingBasket, Coins } from "@lucide/vue";

import type { WorkspaceNavigation } from "./workspace-navigation.types";

export const workspaceNavigation: WorkspaceNavigation = {
  navGroups: [
    {
      title: "Настройки",
      items: [
        { title: "Валюты и курсы", url: "/settings/currency", icon: Coins },
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
