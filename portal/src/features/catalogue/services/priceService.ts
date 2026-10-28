// Service: how prices and stock counts are shown and entered. Amounts are text from the server,
// never converted to numbers (no floating-point maths on money).

import type { Price, PricePayload, PriceState, StockCount, StockPayload } from "../model/types";

const PRICE_PATTERN = /^\d{1,12}(\.\d{1,6})?$/;
const STOCK_PATTERN = /^\d{1,12}(\.\d{1,3})?$/;

export const PRICE_STATE_LABEL: Record<PriceState, string> = {
  current: "Current",
  scheduled: "Scheduled",
  past: "Past",
};

/** "4250.00 INR per each, excluding tax". */
export function priceLine(price: Pick<Price, "unit_price" | "currency" | "unit">): string {
  return `${price.unit_price} ${price.currency} per ${price.unit}`;
}

export function evidenceLabel(price: Pick<Price, "price_list" | "revision">): string {
  return `${price.price_list} list, revision ${price.revision}`;
}

export function checkPriceText(text: string): string | null {
  const value = text.trim();
  if (!PRICE_PATTERN.test(value) || /^0+(\.0+)?$/.test(value)) {
    return "Price: a number above 0 with at most 6 decimals.";
  }
  return null;
}

export function checkStockText(text: string, notTracked: boolean): string | null {
  if (notTracked) return null;
  if (!STOCK_PATTERN.test(text.trim())) return "Quantity: 0 or more, with at most 3 decimals.";
  return null;
}

/** Minutes the zone is ahead of UTC at `instant` (e.g. 330 for Asia/Kolkata). */
function offsetMinutes(instant: number, timeZone: string): number {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    hourCycle: "h23",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).formatToParts(new Date(instant));
  const get = (type: string) => Number(parts.find((part) => part.type === type)?.value ?? 0);
  const asUtc = Date.UTC(get("year"), get("month") - 1, get("day"), get("hour"), get("minute"), get("second"));
  return Math.round((asUtc - instant) / 60000);
}

/**
 * "2026-11-01" -> the ISO instant of midnight that day in the business's time zone (Q8: a
 * scheduled price starts at midnight there). Falls back to UTC when no zone is set.
 */
export function midnightIn(date: string, timeZone: string | null): string {
  const [year = 0, month = 1, day = 1] = date.split("-").map(Number);
  const guess = Date.UTC(year, month - 1, day);
  if (!timeZone) return new Date(guess).toISOString();
  let instant = guess - offsetMinutes(guess, timeZone) * 60000;
  instant = guess - offsetMinutes(instant, timeZone) * 60000; // corrects across a DST change
  return new Date(instant).toISOString();
}

/** Tomorrow on the person's own calendar, as YYYY-MM-DD (the earliest start for a scheduled price). */
export function tomorrow(now: Date = new Date()): string {
  const next = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${next.getFullYear()}-${pad(next.getMonth() + 1)}-${pad(next.getDate())}`;
}

export function pricePayload(
  amount: string,
  startDate: string | null,
  timeZone: string | null,
  note: string,
  commandId: string,
): PricePayload {
  return {
    unit_price: amount.trim(),
    effective_from: startDate ? midnightIn(startDate, timeZone) : null,
    note: note.trim() || null,
    command_id: commandId,
  };
}

/** A datetime-local value ("2026-10-28T09:30", the person's own clock) -> ISO with offset. */
export function localToIso(value: string): string {
  return new Date(value).toISOString();
}

export function stockPayload(
  quantity: string,
  notTracked: boolean,
  asOf: string | null,
  note: string,
  commandId: string,
): StockPayload {
  return {
    quantity: notTracked ? null : quantity.trim(),
    as_of: asOf ? localToIso(asOf) : null,
    note: note.trim() || null,
    command_id: commandId,
  };
}

export function stockLine(count: Pick<StockCount, "quantity" | "unit">): string {
  return count.quantity === null ? "Not tracked" : `${count.quantity} ${count.unit}`;
}

/** "7 days" / "5 minutes" for the business's max stock age. */
export function ageText(seconds: number | null): string {
  if (seconds === null) return "not set";
  if (seconds % 86400 === 0) return `${seconds / 86400} day(s)`;
  if (seconds % 3600 === 0) return `${seconds / 3600} hour(s)`;
  return `${Math.round(seconds / 60)} minute(s)`;
}
