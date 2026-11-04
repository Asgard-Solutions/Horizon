export interface NetworkLocation {
  id: string; server: string; share: string; folder: string; share_path: string; path: string;
  username: string | null; credential_saved: boolean;
}
export interface NetworkInfo {
  hostname: string;
  capabilities: { smb_supported: boolean; credential_store_supported: boolean };
  connections: NetworkLocation[];
  listener: { bind_host: string | null; port: number; lan_reachable: boolean };
  addresses: { url: string; reachable: boolean }[];
}
