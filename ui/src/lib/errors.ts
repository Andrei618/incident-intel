import { z } from "zod";

type ZodIssue = z.core.$ZodIssue;

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export class ValidationError extends ApiError {
  path: string;
  issues: ZodIssue[];
  constructor(path: string, issues: ZodIssue[], received: unknown) {
    super(200, received, "Response from " + path + " failed validation");
    this.name = "ValidationError";
    this.path = path;
    this.issues = issues;
    console.error("Validation failed", { path, issues, received });
  }
}
