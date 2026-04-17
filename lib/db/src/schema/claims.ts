import { pgTable, text, real, timestamp } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const claimsTable = pgTable("claims", {
  id: text("id").primaryKey(),
  userId: text("user_id").notNull(),
  triggerType: text("trigger_type").notNull(),
  incomeImpact: real("income_impact").notNull(),
  payout: real("payout").notNull(),
  status: text("status").notNull().default("approved"),
  fraudScore: real("fraud_score").notNull().default(0),
  explanation: text("explanation").notNull(),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertClaimSchema = createInsertSchema(claimsTable).omit({ createdAt: true });
export type InsertClaim = z.infer<typeof insertClaimSchema>;
export type Claim = typeof claimsTable.$inferSelect;
