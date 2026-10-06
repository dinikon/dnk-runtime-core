import axios from "axios";
import { httpClient } from "@/app/providers/http";
import type {
  Channel,
  Platform,
  PlatformConfig,
  CreateChannel,
  UpdateChannel,
} from "../model/types";
const base = "/console/channels";
export class ChannelRequestError extends Error {
  constructor(
    public status: number | null,
    public fields: Record<string, string>,
  ) {
    super(
      status === 409
        ? "Конфигурация изменилась. Обновите форму перед сохранением."
        : status === 503
          ? "Хранилище ключей подключения пока недоступно. Обратитесь к администратору."
          : status === 404
            ? "Канал или платформа не найдены."
            : status === 422
              ? "Проверьте заполнение формы."
              : "Не удалось выполнить запрос. Повторите попытку.",
    );
  }
}
function safeError(error: unknown) {
  const fields: Record<string, string> = {};
  if (!axios.isAxiosError(error)) return new ChannelRequestError(null, fields);
  const detail: unknown = error.response?.data?.detail;
  if (Array.isArray(detail))
    for (const item of detail) {
      if (item && Array.isArray(item.loc)) {
        const path = item.loc
          .filter((part: unknown) => typeof part === "string")
          .filter((part: string) => part !== "body")
          .join(".");
        fields[path] =
          item.type === "missing" || item.type === "required"
            ? "Обязательное поле."
            : "Некорректное значение.";
      }
    }
  // Axios retains serialized request data on errors; do not retain credentials with UI errors.
  if (error.config) error.config.data = undefined;
  if (error.response?.config) error.response.config.data = undefined;
  return new ChannelRequestError(error.response?.status ?? null, fields);
}
async function write<T>(
  method: "post" | "patch" | "delete",
  url: string,
  data?: CreateChannel | UpdateChannel,
  signal?: AbortSignal,
): Promise<T> {
  try {
    const response = await httpClient.request<T>({ method, url, data, signal });
    response.config.data = undefined;
    return response.data;
  } catch (error) {
    throw safeError(error);
  }
}
export const channelsApi = {
  async kinds(signal?: AbortSignal) {
    return (await httpClient.get<Platform[]>(`${base}/kinds`, { signal })).data;
  },
  async config(kind: string, signal?: AbortSignal) {
    return (
      await httpClient.get<PlatformConfig>(
        `${base}/kinds/${encodeURIComponent(kind)}/config`,
        { signal },
      )
    ).data;
  },
  async list(signal?: AbortSignal) {
    return (await httpClient.get<Channel[]>(base, { signal })).data;
  },
  async get(id: string, signal?: AbortSignal) {
    return (
      await httpClient.get<Channel>(`${base}/${encodeURIComponent(id)}`, {
        signal,
      })
    ).data;
  },
  create: (payload: CreateChannel, signal?: AbortSignal) =>
    write<Channel>("post", base, payload, signal),
  update: (id: string, payload: UpdateChannel, signal?: AbortSignal) =>
    write<Channel>(
      "patch",
      `${base}/${encodeURIComponent(id)}`,
      payload,
      signal,
    ),
  remove: (id: string, signal?: AbortSignal) =>
    write<void>(
      "delete",
      `${base}/${encodeURIComponent(id)}`,
      undefined,
      signal,
    ),
};
