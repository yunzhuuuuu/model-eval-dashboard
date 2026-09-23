import "server-only";

import postgres, { type Sql } from "postgres";

const globalDatabase = globalThis as typeof globalThis & {
  dashboardSql?: Sql;
};

export class ConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ConfigurationError";
  }
}

export function database(): Sql {
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    throw new ConfigurationError(
      "DATABASE_URL is not configured. Connect a Postgres provider before using private datasets.",
    );
  }

  if (!globalDatabase.dashboardSql) {
    globalDatabase.dashboardSql = postgres(databaseUrl, {
      max: 2,
      idle_timeout: 20,
      connect_timeout: 10,
      prepare: false,
    });
  }
  return globalDatabase.dashboardSql;
}
