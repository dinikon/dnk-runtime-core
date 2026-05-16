import { QueryClient, VueQueryPlugin } from "@tanstack/vue-query";
import { createPinia } from "pinia";
import { createApp } from "vue";

import App from "./app/App.vue";
import { router } from "./app/router";
import "./style.css";

const app = createApp(App);
const queryClient = new QueryClient();

app.use(createPinia());
app.use(VueQueryPlugin, { queryClient });
app.use(router);

app.mount("#app");
