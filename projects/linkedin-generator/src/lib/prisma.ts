import { PrismaClient } from "@prisma/client";
import { PrismaPg } from "@prisma/adapter-pg";
import { Pool } from "pg";

declare global {
  var __prisma: PrismaClient | undefined;
  var __pool: Pool | undefined;
}

function getPool(): Pool {
  if (!global.__pool) {
    const connectionString = process.env.DATABASE_URL;
    if (!connectionString) {
      throw new Error("DATABASE_URL environment variable is not set");
    }
    global.__pool = new Pool({ connectionString });
  }
  return global.__pool;
}

function getPrismaClient(): PrismaClient {
  if (!global.__prisma) {
    const adapter = new PrismaPg(getPool());
    global.__prisma = new PrismaClient({ adapter });
  }
  return global.__prisma;
}

// Only initialize if we have DATABASE_URL (skip during build)
let prisma: PrismaClient;

if (process.env.DATABASE_URL) {
  prisma = getPrismaClient();
} else {
  // Return a dummy that throws on use - for build time only
  prisma = new Proxy({} as PrismaClient, {
    get() {
      throw new Error("DATABASE_URL not available");
    },
  });
}

export { prisma };
