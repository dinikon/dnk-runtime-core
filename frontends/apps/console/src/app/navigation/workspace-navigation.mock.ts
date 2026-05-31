import {
  Building2,
  Command,
  ContactRound,
  Frame,
  LayoutDashboard,
  LifeBuoy,
  MessageSquareText,
  PieChart,
  Settings2,
} from "lucide-vue-next";

import type { WorkspaceNavigation } from "./workspace-navigation.types";

export function getWorkspaceNavigationMock(): WorkspaceNavigation {
  return {
    brand: {
      name: "dNiko",
      description: "Workspace",
      url: "/dashboard",
      icon: Command,
    },
    navMain: [
      {
        title: "Dashboard",
        url: "/dashboard",
        icon: LayoutDashboard,
      },
      {
        title: "CRM",
        url: "/crm/contacts",
        icon: ContactRound,
        items: [
          {
            title: "Contacts",
            url: "/crm/contacts",
          },
        ],
      },
      {
        title: "Workspace",
        url: "/dashboard",
        icon: Building2,
        items: [
          {
            title: "Overview",
            url: "/dashboard",
          },
        ],
      },
      {
        title: "Settings",
        url: "/dashboard",
        icon: Settings2,
        items: [
          {
            title: "General",
            url: "/dashboard",
          },
        ],
      },
    ],
    navSecondary: [
      {
        title: "Support",
        url: "/dashboard",
        icon: LifeBuoy,
      },
      {
        title: "Feedback",
        url: "/dashboard",
        icon: MessageSquareText,
      },
    ],
    projects: [
      {
        name: "Operations",
        url: "/dashboard",
        icon: Frame,
      },
      {
        name: "Sales",
        url: "/crm/contacts",
        icon: PieChart,
      },
    ],
  };
}
