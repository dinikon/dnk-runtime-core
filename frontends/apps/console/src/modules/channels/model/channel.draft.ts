import type {
  Platform,
  Channel,
  ChannelDraft,
  ChannelSave,
  JsonObject,
} from "./channel.types";
import { schemaFields } from "./channel.schema.ts";

export function draftFor(platform: Platform, channel?: Channel): ChannelDraft {
  return {
    name: channel?.name ?? "",
    platformKind: platform.kind,
    endpoint:
      channel?.config.endpoint ??
      schemaFields(platform.configSchema)
        .find((f) => f.key === "endpoint")
        ?.defaultValue?.toString() ??
      "",
    settings: JSON.parse(
      JSON.stringify(
        Object.fromEntries(
          schemaFields(platform.configSchema, "settings").map((field) => [
            field.key,
            channel?.config.settings[field.key] ?? field.defaultValue,
          ]),
        ),
      ),
    ) as JsonObject,
    credentials: Object.fromEntries(
      schemaFields(platform.credentialsSchema).map((field) => [field.key, ""]),
    ),
    replaceCredentials: !channel,
  };
}
export function saveDraft(
  draft: ChannelDraft,
  platform: Platform,
): ChannelSave {
  return {
    name: draft.name,
    platformKind: platform.kind,
    config: {
      version: platform.configVersion,
      endpoint: draft.endpoint,
      settings: {
        ...(JSON.parse(JSON.stringify(draft.settings)) as JsonObject),
      },
    },
    ...(draft.replaceCredentials
      ? { credentials: { ...draft.credentials } }
      : {}),
  };
}
