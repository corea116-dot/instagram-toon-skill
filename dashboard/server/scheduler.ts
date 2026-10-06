import type { Schedule } from "../shared/types";
const OFFSET = 9 * 3600_000;
export function koreaDate(date: Date) {
  return new Date(date.getTime() + OFFSET).toISOString().slice(0, 10);
}
export function slotOn(day: string, time: string) {
  return new Date(`${day}T${time}:00+09:00`).toISOString();
}
export function latestDue(schedule: Schedule, now: Date): string | null {
  if (!schedule.enabled) return null;
  // Recurring schedules use Korea time. Pick only the newest missed slot, including after a long shutdown.
  for (let offset = 0; offset < 8; offset++) {
    const day = koreaDate(new Date(now.getTime() - offset * 86400_000));
    const weekday = new Date(`${day}T00:00:00+09:00`).getUTCDay();
    const localWeekday = (weekday + 1) % 7;
    const slot = slotOn(day, schedule.time);
    if (
      schedule.days.includes(localWeekday) &&
      slot <= now.toISOString() &&
      slot >= schedule.createdAt &&
      (!schedule.lastSlot || slot > schedule.lastSlot)
    )
      return slot;
  }
  return null;
}
export function publishForSlot(schedule: Schedule, slot: string): string {
  let publish = slotOn(koreaDate(new Date(slot)), schedule.publishTime);
  if (schedule.publishTime < schedule.time)
    publish = new Date(new Date(publish).getTime() + 86400_000).toISOString();
  return publish;
}
export function nextSlot(schedule: Schedule, now: Date): string | null {
  if (!schedule.enabled) return null;
  for (let i = 0; i < 8; i++) {
    const day = koreaDate(new Date(now.getTime() + i * 86400_000));
    const slot = slotOn(day, schedule.time);
    const weekday = new Date(`${day}T12:00:00+09:00`).getUTCDay();
    if (schedule.days.includes(weekday) && slot > now.toISOString())
      return slot;
  }
  return null;
}
