import { CreditCard, Plug, Settings2, Users } from "@lucide/vue";

import type { AdminNavigationGroup } from "./admin-navigation.types";

export const adminNavigation: AdminNavigationGroup[] = [
  {
    title: "Модули",
    items: [
      {
        title: "Точки контакта",
        icon: Settings2,
        url: "/admin/contact-points",
        requiredRole: "admin",
      },
    ],
  },
  {
    title: "Общие",
    hidden: true,
    items: [
      {
        title: "Настройки пространства",
        icon: Settings2,
        disabled: true,
        requiredRole: "admin",
      },
    ],
  },
  {
    title: "Доступ",
    items: [
      {
        title: "Пользователи",
        icon: Users,
        url: "/admin/users",
        requiredRole: "admin",
      },
    ],
  },
  {
    title: "Биллинг",
    hidden: true,
    items: [
      {
        title: "Подписка и счета",
        icon: CreditCard,
        disabled: true,
        requiredRole: "admin",
      },
    ],
  },
  {
    title: "Интеграции",
    hidden: true,
    items: [
      {
        title: "Подключения",
        icon: Plug,
        disabled: true,
        requiredRole: "admin",
      },
    ],
  },
];
