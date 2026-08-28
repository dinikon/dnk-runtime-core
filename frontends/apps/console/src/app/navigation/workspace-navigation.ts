import { LifeBuoy } from "@lucide/vue";

import type { WorkspaceNavigation } from "./workspace-navigation.types";

export const workspaceNavigation: WorkspaceNavigation = {
  navGroups: [],
  support: {
    title: "Support",
    url: "https://t.me/iNikon",
    icon: LifeBuoy,
    external: true,
  },
};
