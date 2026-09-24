import { QueryClient, VueQueryPlugin } from "@tanstack/vue-query";
import { createPinia } from "pinia";
import { createApp } from "vue";

import App from "./app/App.vue";
import { installHttpInterceptors } from "./app/providers/http";
import { installRouterGuards, router } from "./app/router";
import "./style.css";

const app = createApp(App);
const queryClient = new QueryClient();
const pinia = createPinia();

app.use(pinia);
installHttpInterceptors(router, pinia);
app.use(VueQueryPlugin, { queryClient });
installRouterGuards(pinia);
app.use(router);

app.mount("#app");
