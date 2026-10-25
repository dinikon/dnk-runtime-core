import { httpClient } from "@/app/providers/http";
import {
  importConfigurationToDto,
  importDetailsFromDto,
  importRowFromDto,
  importRunFromDto,
} from "./import.mapper";
import type * as DTO from "./import.dto";
import type {
  CatalogImportDetails,
  ImportActionResult,
  ImportConfiguration,
  ImportPage,
  ImportRowsPage,
  ImportSourceValues,
} from "../model/import.types";
const base = "/console/catalog/imports";
export const catalogImportApi = {
  async create(value: ImportSourceValues): Promise<ImportActionResult> {
    let payload:
      FormData | { url: string; default_locale: string; timezone: string };
    if (value.file) {
      payload = new FormData();
      payload.append("file", value.file);
      payload.append("default_locale", value.defaultLocale);
      payload.append("timezone", value.timezone);
    } else
      payload = {
        url: value.url.trim(),
        default_locale: value.defaultLocale,
        timezone: value.timezone,
      };
    return (
      await httpClient.post<DTO.CreateImportResponse>(base, payload, {
        headers: {
          "Idempotency-Key": value.key,
          ...(value.file ? { "Content-Type": undefined } : {}),
        },
        timeout: 600000,
      })
    ).data;
  },
  async list(page: number, signal?: AbortSignal): Promise<ImportPage> {
    const { data } = await httpClient.get<DTO.ListImportsResponse>(base, {
      params: { offset: (page - 1) * 20, limit: 20 },
      signal,
    });
    return { items: data.items.map(importRunFromDto), total: data.total };
  },
  async get(id: string, signal?: AbortSignal): Promise<CatalogImportDetails> {
    return importDetailsFromDto(
      (
        await httpClient.get<DTO.GetImportResponse>(
          `${base}/${encodeURIComponent(id)}`,
          { signal },
        )
      ).data,
    );
  },
  async configure(
    id: string,
    configuration: ImportConfiguration,
  ): Promise<ImportActionResult> {
    return (
      await httpClient.put<DTO.ConfigureImportResponse>(
        `${base}/${encodeURIComponent(id)}/configuration`,
        importConfigurationToDto(configuration),
      )
    ).data;
  },
  async start(id: string, version: number): Promise<ImportActionResult> {
    return (
      await httpClient.post<DTO.StartImportResponse>(
        `${base}/${encodeURIComponent(id)}/start`,
        { version },
      )
    ).data;
  },
  async resume(id: string, generation: number): Promise<ImportActionResult> {
    return (
      await httpClient.post<DTO.ResumeImportResponse>(
        `${base}/${encodeURIComponent(id)}/resume`,
        { generation },
      )
    ).data;
  },
  async cancel(id: string): Promise<ImportActionResult> {
    return (
      await httpClient.post<DTO.CancelImportResponse>(
        `${base}/${encodeURIComponent(id)}/cancel`,
      )
    ).data;
  },
  async rows(
    id: string,
    page: number,
    outcome: string,
    signal?: AbortSignal,
  ): Promise<ImportRowsPage> {
    const { data } = await httpClient.get<DTO.ListImportRowsResponse>(
      `${base}/${encodeURIComponent(id)}/rows`,
      {
        params: {
          offset: (page - 1) * 50,
          limit: 50,
          outcome: outcome || undefined,
        },
        signal,
      },
    );
    return { items: data.items.map(importRowFromDto), total: data.total };
  },
  async report(id: string): Promise<Blob> {
    return (
      await httpClient.get<Blob>(
        `${base}/${encodeURIComponent(id)}/report.csv`,
        { responseType: "blob" },
      )
    ).data;
  },
};
