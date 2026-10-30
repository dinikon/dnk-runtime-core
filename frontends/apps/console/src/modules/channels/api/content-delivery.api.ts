import { httpClient } from "@/app/providers/http";
import type {
  ContentDelivery,
  RequestContentDeliveryInput,
  ReconcileContentDeliveryInput,
} from "../model/content-delivery.types";
import type {
  GetContentDeliveriesResponseDto,
  RequestContentDeliveryResponseDto,
  RequestContentReconciliationResponseDto,
} from "./content-delivery.dto";
import {
  contentDelivery,
  contentDeliveryPayload,
  contentReconciliationPayload,
} from "./content-delivery.mapper";

function path(channelId: string, groupId: string): string {
  return `/console/channels/${encodeURIComponent(channelId)}/catalog-bindings/${encodeURIComponent(groupId)}/content-deliveries`;
}

export async function getContentDeliveries(
  channelId: string,
  groupId: string,
  signal?: AbortSignal,
): Promise<ContentDelivery[]> {
  const { data } = await httpClient.get<GetContentDeliveriesResponseDto>(
    path(channelId, groupId),
    { signal },
  );
  return data.items.map(contentDelivery);
}

export async function requestContentDelivery(
  input: RequestContentDeliveryInput,
): Promise<ContentDelivery[]> {
  const { data } = await httpClient.post<RequestContentDeliveryResponseDto>(
    path(input.channelId, input.groupId),
    contentDeliveryPayload(input),
  );
  return data.items.map(contentDelivery);
}

export async function requestContentReconciliation(
  input: ReconcileContentDeliveryInput,
): Promise<ContentDelivery[]> {
  const { data } =
    await httpClient.post<RequestContentReconciliationResponseDto>(
      `${path(input.channelId, input.groupId)}/${encodeURIComponent(input.publicationId)}/reconcile`,
      contentReconciliationPayload(input),
    );
  return data.items.map(contentDelivery);
}
