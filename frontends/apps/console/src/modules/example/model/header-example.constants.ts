import type { HeaderExample } from "./header-example.types";

const projectDescription =
  "Manage your project’s details such as name, image, description and settings.";
const profileDescription =
  "Manage your profile details such as name, avatar, email and bio.";

export const headerExamples = [
  {
    variant: "breadcrumbs",
    number: 2,
    title: "Project alpha",
    description: projectDescription,
  },
  {
    variant: "tabs-top",
    number: 3,
    title: "Project alpha",
    description: profileDescription,
  },
  {
    variant: "search",
    number: 4,
    title: "Project alpha",
    description: profileDescription,
  },
  { variant: "compact", number: 5, title: "Project alpha" },
  {
    variant: "profile",
    number: 6,
    title: "John Doe",
    description: "hi@example.com",
  },
  {
    variant: "tabs-bottom",
    number: 7,
    title: "Profile details",
    description: profileDescription,
  },
  {
    variant: "search-avatar",
    number: 8,
    title: "Project alpha",
    description: projectDescription,
  },
] as const satisfies readonly HeaderExample[];

export const headerExampleTabs = [
  { value: "profile", label: "Profile" },
  { value: "reports", label: "Reports" },
  { value: "analytics", label: "Analytics" },
  { value: "notifications", label: "Notifications" },
  { value: "help-center", label: "Help Center" },
] as const;

export const headerExampleBreadcrumbs = [
  { id: "home", label: "Home" },
  { id: "settings", label: "Settings" },
  { id: "profile-details", label: "Profile details" },
] as const;
