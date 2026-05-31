import {
  Building2,
  ContactRound,
  LifeBuoy,
  Link2,
  SquareStack,
  Truck,
  List,
} from "lucide-vue-next";

import type { WorkspaceNavigation } from "./workspace-navigation.types";

export const workspaceNavigation: WorkspaceNavigation = {
  navGroups: [
    {
      title: "CRM",
      items: [
        {
          title: "Contacts",
          url: "/crm/contacts",
          icon: List,
          defaultOpen: true,
          items: [
            {
              title: "Contact",
              url: "/crm/contacts",
              icon: ContactRound,
            },
            {
              title: "Company",
              url: "/crm/companies",
              icon: Building2,
            },
          ],
        },
      ],
    },
    {
      title: "CDP",
      items: [
        {
          title: "Delivery",
          url: "/cdp/delivery",
          icon: Truck,
        },
        {
          title: "Template",
          url: "/cdp/templates",
          icon: SquareStack,
        },
      ],
    },
    {
      title: "Settings",
      items: [
        {
          title: "Connection's",
          url: "/settings/connections",
          icon: Link2,
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
