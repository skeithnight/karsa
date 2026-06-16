export function formatDuration(secondsRaw: number): string {
  if (secondsRaw === null || secondsRaw === undefined) return "N/A";
  const h = Math.floor(secondsRaw / 3600);
  const m = Math.floor((secondsRaw % 3600) / 60);
  const s = secondsRaw % 60;
  return [h, m > 9 ? m : h ? '0' + m : m || '0', s > 9 ? s : '0' + s].filter(Boolean).join(':');
}
