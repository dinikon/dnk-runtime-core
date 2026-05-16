import {createRouter, createWebHistory} from "vue-router";

import {ContactsPage} from "@/features/crm";
import LoginPage from "@/pages/auth/LoginPage.vue";

export const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: "/",
            redirect: "/crm/contacts"
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
            path: "/crm/contacts",
            name: "crm-contacts",
            component: ContactsPage
        }
    ]
});
