import {
  LifeBuoy,
  Link2,
  PlugZap,
  SquareStack,
  Truck,
  Workflow,
} from "@lucide/vue";

import type { WorkspaceNavigation } from "./workspace-navigation.types";

export const workspaceNavigation: WorkspaceNavigation = {
  navGroups: [
    {
      title: "Workflow",
      items: [
        {
          title: "Workflows",
          url: "/workflows",
          icon: Workflow,
        },
      ],
    },
    {
      title: "CDP",
      items: [
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
