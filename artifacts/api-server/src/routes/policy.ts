import { Router, type IRouter } from "express";
import { db, policiesTable, usersTable } from "@workspace/db";
import { eq } from "drizzle-orm";
import { CreatePolicyBody, GetUserPolicyParams, GetUserPolicyResponse } from "@workspace/api-zod";
import { randomUUID } from "crypto";

const router: IRouter = Router();

const coverageMultipliers: Record<string, number> = {
  basic: 2,
  standard: 3,
  premium: 5,
};

const premiumMultipliers: Record<string, number> = {
  basic: 0.8,
  standard: 1.0,
  premium: 1.4,
};

router.post("/policy/create", async (req, res): Promise<void> => {
  const parsed = CreatePolicyBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  const { userId, coverageType } = parsed.data;
  const [user] = await db.select().from(usersTable).where(eq(usersTable.id, userId));
  if (!user) {
    res.status(404).json({ error: "User not found" });
    return;
  }

  const lossRatio = 0.065;
  const riskFactor = user.riskScore / 100;
  const basePremium = user.income * riskFactor * lossRatio * 7;
  const premium = Math.round(basePremium * (premiumMultipliers[coverageType] ?? 1.0));
  const coverage = Math.round(user.income * (coverageMultipliers[coverageType] ?? 3));

  const today = new Date();
  const nextMonth = new Date(today);
  nextMonth.setMonth(nextMonth.getMonth() + 1);

  const policyId = randomUUID();
  const [policy] = await db.insert(policiesTable).values({
    id: policyId,
    userId,
    coverageType,
    premium,
    coverage,
    status: "active",
    startDate: today.toISOString().split("T")[0],
    nextPaymentDate: nextMonth.toISOString().split("T")[0],
    claimsCount: 0,
    totalPaidOut: 0,
  }).returning();

  req.log.info({ policyId, userId, coverageType }, "Policy created");
  res.status(201).json(GetUserPolicyResponse.parse({
    ...policy,
  }));
});

router.get("/policy/:userId", async (req, res): Promise<void> => {
  const rawId = Array.isArray(req.params.userId) ? req.params.userId[0] : req.params.userId;
  const params = GetUserPolicyParams.safeParse({ userId: rawId });
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const [policy] = await db
    .select()
    .from(policiesTable)
    .where(eq(policiesTable.userId, params.data.userId))
    .orderBy(policiesTable.createdAt);

  if (!policy) {
    res.status(404).json({ error: "No policy found for user" });
    return;
  }

  res.json(GetUserPolicyResponse.parse(policy));
});

export default router;
