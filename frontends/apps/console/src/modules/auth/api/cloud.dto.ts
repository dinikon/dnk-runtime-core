export interface CloudStatusDto {
  enabled: boolean;
  linked: boolean;
}

export interface CloudStartRequestDto {
  purpose: "login" | "link";
  silent: boolean;
}

export interface CloudStartResponseDto {
  authorization_url: string;
}
