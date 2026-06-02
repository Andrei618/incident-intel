import { nextStates } from "./ticketTransitions";

it("open allows in_progress and closed", () => {
  const result = nextStates("open");
  expect(result).toContain("in_progress");
  expect(result).toContain("closed");
});

it("open does not allow resolved", () => {
  expect(nextStates("open")).not.toContain("resolved");
});

it("closed returns empty array", () => {
  expect(nextStates("closed")).toHaveLength(0);
});

it("in_progress allows resolved", () => {
  expect(nextStates("in_progress")).toContain("resolved");
});

it("in_progress does not allow closed", () => {
  expect(nextStates("in_progress")).not.toContain("closed");
});

it("resolved allows closed", () => {
  expect(nextStates("resolved")).toContain("closed");
});
