import { httpClient } from "@/app/providers/http";
export const saveDisplayCurrency = async (display_currency: string | null) =>
  (
    await httpClient.put<{ display_currency: string | null }>(
      "/console/auth/me/display-currency",
      { display_currency },
    )
  ).data;
