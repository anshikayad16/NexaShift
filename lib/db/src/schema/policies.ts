import { pgTable, text, real, integer, timestamp } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const policiesTable = pgTable("policies", {
  id: text("id").primaryKey(),
  userId: text("user_id").notNull(),
  coverageType: text("coverage_type").notNull(),
  premium: real("premium").notNull(),
  coverage: real("coverage").notNull(),
  status: text("status").notNull().default("active"),
  startDate: text("start_date").notNull(),
  nextPaymentDate: text("next_payment_date").notNull(),
  claimsCount: integer("claims_count").notNull().default(0),
  totalPaidOut: real("total_paid_out").notNull().default(0),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertPolicySchema = createInsertSchema(policiesTable).omit({ createdAt: true });
export type InsertPolicy = z.infer<typeof insertPolicySchema>;
export type Policy = typeof policiesTable.$inferSelect;
