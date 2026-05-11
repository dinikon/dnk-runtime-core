import {createRouter, createWebHistory} from "vue-router";

import {
    CommunicationMessagesPage,
    CommunicationProvidersPage,
    CommunicationTemplatesPage,
    DataModelObjectFieldsPage,
    DataModelObjectsPage,
    ProfileSettingsPage,
    SettingsPlaceholderPage
} from "@/features/settings";
import HomePage from "@/pages/HomePage.vue";
import LoginPage from "@/pages/auth/LoginPage.vue";

const placeholderSettingsRoutes = [
    settingsPlaceholderRoute("/settings/experience", "settings-experience", "Experience", "experience", [
        {label: "User"},
        {label: "Experience"}
    ]),
    settingsPlaceholderRoute("/settings/accounts", "settings-accounts", "Accounts", "accounts", [
        {label: "User"},
        {label: "Accounts"}
    ]),
    settingsPlaceholderRoute("/settings/accounts/emails", "settings-emails", "Emails", "emails", [
        {label: "User"},
        {label: "Accounts", to: "/settings/accounts"},
        {label: "Emails"}
    ]),
    settingsPlaceholderRoute("/settings/accounts/calendar", "settings-calendar", "Calendar", "calendar", [
        {label: "User"},
        {label: "Accounts", to: "/settings/accounts"},
        {label: "Calendar"}
    ]),
    settingsPlaceholderRoute("/settings/workspace/general", "settings-workspace-general", "General", "workspace-general", [
        {label: "Workspace"},
        {label: "General"}
    ]),
    settingsPlaceholderRoute("/settings/workspace/members", "settings-members", "Members", "members", [
        {label: "Workspace"},
        {label: "Members"}
    ]),
    settingsPlaceholderRoute("/settings/workspace/roles", "settings-roles", "Roles", "roles", [
        {label: "Workspace"},
        {label: "Roles"}
    ]),
    settingsPlaceholderRoute("/settings/workspace/domains", "settings-domains", "Domains", "domains", [
        {label: "Workspace"},
        {label: "Domains"}
    ]),
    settingsPlaceholderRoute("/settings/workspace/billing", "settings-billing", "Billing", "billing", [
        {label: "Workspace"},
        {label: "Billing"}
    ]),
    settingsPlaceholderRoute("/settings/workspace/apis-webhooks", "settings-apis-webhooks", "APIs & Webhooks", "apis-webhooks", [
        {label: "Workspace"},
        {label: "APIs & Webhooks"}
    ]),
    settingsPlaceholderRoute("/settings/workspace/apps", "settings-apps", "Apps", "apps", [
        {label: "Workspace"},
        {label: "Apps"}
    ]),
    settingsPlaceholderRoute("/settings/workspace/ai", "settings-ai", "AI", "ai", [
        {label: "Workspace"},
        {label: "AI"}
    ]),
    settingsPlaceholderRoute("/settings/workspace/security", "settings-security", "Security", "security", [
        {label: "Workspace"},
        {label: "Security"}
    ]),
    settingsPlaceholderRoute("/settings/admin-panel", "settings-admin-panel", "Admin Panel", "admin-panel", [
        {label: "Other"},
        {label: "Admin Panel"}
    ]),
    settingsPlaceholderRoute("/settings/updates", "settings-updates", "Updates", "updates", [
        {label: "Other"},
        {label: "Updates"}
    ]),
    settingsPlaceholderRoute("/settings/support", "settings-support", "Support", "support", [
        {label: "Other"},
        {label: "Support"}
    ]),
    settingsPlaceholderRoute("/settings/documentation", "settings-documentation", "Documentation", "documentation", [
        {label: "Other"},
        {label: "Documentation"}
    ])
];

export const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: "/",
            name: "home",
            component: HomePage
        },
        {
            path: "/login",
            name: "login",
            component: LoginPage,
            meta: {
                layout: "auth"
            }
        },
        {
            path: "/settings",
            redirect: "/settings/profile"
        },
        {
            path: "/settings/profile",
            name: "settings-profile",
            component: ProfileSettingsPage
        },
        {
            path: "/settings/workspace/data-model",
            name: "settings-data-model",
            component: DataModelObjectsPage
        },
        {
            path: "/settings/workspace/data-model/:objectId",
            name: "settings-data-model-object",
            component: DataModelObjectFieldsPage
        },
        {
            path: "/settings/workspace/communication/providers",
            name: "settings-communication-providers",
            component: CommunicationProvidersPage
        },
        {
            path: "/settings/workspace/communication/templates",
            name: "settings-communication-templates",
            component: CommunicationTemplatesPage
        },
        {
            path: "/settings/workspace/communication/messages",
            name: "settings-communication-messages",
            component: CommunicationMessagesPage
        },
        ...placeholderSettingsRoutes
    ]
});

function settingsPlaceholderRoute(
    path: string,
    name: string,
    title: string,
    activeItem: string,
    breadcrumbs: Array<{ label: string; to?: string }>
) {
    return {
        path,
        name,
        component: SettingsPlaceholderPage,
        meta: {
            settingsTitle: title,
            settingsActiveItem: activeItem,
            settingsBreadcrumbs: breadcrumbs
        }
    };
}
