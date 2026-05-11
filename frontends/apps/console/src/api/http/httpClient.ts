import axios from "axios";

import {apiBaseUrl} from "@/shared/config/env";

export const httpClient = axios.create({
    baseURL: apiBaseUrl,
    withCredentials: true,
    headers: {
        "Content-Type": "application/json",
        Accept: "application/json"
    }
});
