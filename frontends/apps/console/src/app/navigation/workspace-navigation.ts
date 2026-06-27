import {
  Building2,
  ContactRound,
  LifeBuoy,
  Link2,
  PlugZap,
  SquareStack,
  Truck,
  List,
  Workflow,
} from "@lucide/vue";

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
          title: "Workflows",
          url: "/workflows",
          icon: Workflow,
        },
        {
          title: "Providers",
          url: "/cdp/providers",
          icon: PlugZap,
        },
        {
          title: "Connections",
          url: "/cdp/connections",
          icon: Link2,
        },
        {
          title: "Templates",
          url: "/cdp/templates",
          icon: SquareStack,
        },
        {
          title: "Deliveries",
          url: "/cdp/deliveries",
          icon: Truck,
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
