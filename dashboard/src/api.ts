export async function api<T = any>(
  path: string,
  body?: unknown,
  method?: string,
): Promise<T> {
  const response = await fetch("/api" + path, {
    method: method ?? (body === undefined ? "GET" : "POST"),
    headers:
      body === undefined
        ? {}
        : { "Content-Type": "application/json", "X-Toon-Desk": "1" },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const result = await response.json();
  if (!response.ok)
    throw new Error(result.error ?? "요청을 마치지 못했습니다.");
  return result;
}
export function imageUrl(episode: string, file: string, thumb = false) {
  return `/api/episodes/${encodeURIComponent(episode)}/image?file=${encodeURIComponent(file)}${thumb ? "&thumb=1" : ""}`;
}
export function dateText(value: string | undefined) {
  return value
    ? new Intl.DateTimeFormat("ko-KR", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "Asia/Seoul",
      }).format(new Date(value))
    : "아직 없음";
}
export function localInput(iso: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);
}
