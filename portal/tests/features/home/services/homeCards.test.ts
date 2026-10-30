import { describe, expect, it } from "vitest";

import type { Permission } from "@/features/auth";
import {
  allDone,
  countText,
  greeting,
  homeCards,
  setupProgress,
  type CountResult,
  type HomeCardId,
} from "@/features/home/services/homeCards";

const loaded = (count: number): CountResult => ({ count, failed: false });
const COUNTS: Record<HomeCardId, CountResult> = {
  approve: loaded(3),
  changes: loaded(0),
  requests: loaded(2),
  orders: loaded(1),
};

function allowing(...permissions: Permission[]) {
  return (permission: Permission) => permissions.includes(permission);
}

describe("homeCards", () => {
  it("returns only the cards the person may use, in a fixed order", () => {
    const cards = homeCards(allowing("enquiries:view", "quotations:approve"), COUNTS);
    expect(cards.map((card) => card.id)).toEqual(["approve", "requests"]);
    expect(cards[0]?.link).toBe("/quotations?filter=waiting");
  });

  it("shows a full first page as 50+, and unknown counts never as 0", () => {
    expect(countText(loaded(7))).toBe("7");
    expect(countText(loaded(50))).toBe("50+");
    expect(countText({ count: undefined, failed: false })).toBe("…");
    expect(countText({ count: undefined, failed: true })).toBe("?");
  });

  it("says all done only when every card has loaded and is zero", () => {
    const zero = { approve: loaded(0), changes: loaded(0), requests: loaded(0), orders: loaded(0) };
    const can = allowing("quotations:approve", "enquiries:view");
    expect(allDone(homeCards(can, zero))).toBe(true);
    expect(allDone(homeCards(can, { ...zero, requests: { count: undefined, failed: false } }))).toBe(false);
    expect(allDone(homeCards(can, COUNTS))).toBe(false);
    expect(allDone([])).toBe(false);
  });

  it("greets by the time of day and counts setup steps", () => {
    expect(greeting(8)).toBe("Good morning");
    expect(greeting(13)).toBe("Good afternoon");
    expect(greeting(20)).toBe("Good evening");
    expect(setupProgress([{ done: true }, { done: false }, { done: true }])).toEqual({ done: 2, total: 3 });
  });
});
