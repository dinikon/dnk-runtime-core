import { httpClient } from "@/app/providers/http";
import type {
  BindingDto,
  BindingPageDto,
  BindingCandidatesDto,
  BindingPreviewDto,
} from "./binding.dto";
import {
  bindingPosition,
  bindingPreview,
  catalogBinding,
  bindingProposal,
} from "./binding.mapper";
import type {
  BindingFilters,
  BindingPage,
  BindingCandidateFilters,
  BindingCandidates,
  BindingProposal,
  BindingPreview,
  CatalogBinding,
} from "../model/bindings/binding.types";
const root = (id: string): string =>
  `/console/channels/${encodeURIComponent(id)}`;
export const bindingApi = {
  async list(f: BindingFilters, signal?: AbortSignal): Promise<BindingPage> {
    const { data } = await httpClient.get<BindingPageDto>(
      "/console/channels/catalog-bindings",
      {
        params: {
          catalog_item_id: f.catalogRootId || undefined,
          mode: f.mode,
          channel_id: f.channelId || undefined,
          publication_id: f.publicationId || undefined,
          locale: f.locale,
          offset: f.offset,
          limit: f.limit,
        },
        signal,
      },
    );
    return { ...data, items: data.items.map(catalogBinding) };
  },
  async get(
    channelId: string,
    id: string,
    locale: string,
    signal?: AbortSignal,
  ): Promise<CatalogBinding> {
    const { data } = await httpClient.get<{ binding: BindingDto }>(
      `${root(channelId)}/catalog-bindings/${encodeURIComponent(id)}`,
      { params: { locale }, signal },
    );
    return catalogBinding(data.binding);
  },
  async candidates(
    kind: "catalog" | "publication",
    f: BindingCandidateFilters,
    signal?: AbortSignal,
  ): Promise<BindingCandidates> {
    const { data } = await httpClient.get<BindingCandidatesDto>(
      `${root(f.channelId)}/${kind === "catalog" ? "catalog-binding-candidates" : "publication-binding-candidates"}`,
      {
        params: {
          mode: f.mode,
          locale: f.locale,
          search: f.search,
          offset: f.offset,
          limit: f.limit,
        },
        signal,
      },
    );
    return {
      items: data.items.map(bindingPosition),
      occupiedIds: data.occupied_ids,
      total: data.total,
      offset: data.offset,
      limit: data.limit,
    };
  },
  async preview(
    channelId: string,
    proposal: BindingProposal,
    signal?: AbortSignal,
  ): Promise<BindingPreview> {
    const { data } = await httpClient.post<{ preview: BindingPreviewDto }>(
      `${root(channelId)}/catalog-bindings/preview`,
      bindingProposal(proposal),
      { signal },
    );
    return bindingPreview(data.preview);
  },
  async create(
    channelId: string,
    proposal: BindingProposal,
    preview: BindingPreview,
  ): Promise<{ id: string; revision: number }> {
    const body = bindingProposal(proposal);
    delete body.group_id;
    return (
      await httpClient.post<{ id: string; revision: number }>(
        `${root(channelId)}/catalog-bindings`,
        {
          ...body,
          catalog_token: preview.catalogToken,
          publication_token: preview.publicationToken,
        },
      )
    ).data;
  },
  async update(
    channelId: string,
    id: string,
    revision: number,
    proposal: BindingProposal,
    preview: BindingPreview,
  ): Promise<{ id: string; revision: number }> {
    return (
      await httpClient.put<{ id: string; revision: number }>(
        `${root(channelId)}/catalog-bindings/${encodeURIComponent(id)}`,
        {
          expected_revision: revision,
          items: bindingProposal(proposal).items,
          catalog_token: preview.catalogToken,
          publication_token: preview.publicationToken,
          locale: proposal.locale,
        },
      )
    ).data;
  },
  async remove(channelId: string, id: string, revision: number): Promise<void> {
    await httpClient.delete(
      `${root(channelId)}/catalog-bindings/${encodeURIComponent(id)}`,
      { params: { expected_revision: revision } },
    );
  },
};
