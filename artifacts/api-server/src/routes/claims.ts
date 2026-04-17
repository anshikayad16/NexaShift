import { Router, type IRouter } from "express";
import { db, claimsTable, policiesTable, usersTable } from "@workspace/db";
import { eq } from "drizzle-orm";
import {
  ProcessClaimBody,
  ProcessClaimResponse,
  GetUserClaimsParams,
  GetUserClaimsResponse,
} from "@workspace/api-zod";
import { randomUUID } from "crypto";

const router: IRouter = Router();

const TRIGGER_DESCRIPTIONS: Record<string, string> = {
  rain: "Heavy rainfall disrupted delivery routes, reducing trips by 40%",
  aqi: "Poor air quality (AQI >200) made outdoor work unsafe",
  heat: "Extreme heat warning reduced rider availability by 35%",
  platform_outage: "App platform outage blocked order acceptance for 3+ hours",
  upi_downtime: "UPI payment gateway downtime prevented collections",
};

function computeFraudScore(userId: string, incomeImpact: number, triggerType: string): number {
  let score = Math.random() * 30;
  if (incomeImpact > 10000) score += 15;
  if (triggerType === "upi_downtime") score += 5;
  return Math.min(Math.round(score), 95);
}

function computeTrustScore(userId: string, fraudScore: number): number {
  return Math.round(100 - fraudScore + Math.random() * 10);
}

function computePayout(incomeImpact: number, fraudScore: number, coverage: number): number {
  const fraudMultiplier = fraudScore > 60 ? 0.5 : fraudScore > 40 ? 0.75 : 0.9;
  const rawPayout = incomeImpact * fraudMultiplier;
  return Math.min(Math.round(rawPayout), coverage * 0.3);
}

router.post("/claim/process", async (req, res): Promise<void> => {
  const parsed = ProcessClaimBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  const { userId, triggerType, incomeImpact } = parsed.data;

  const [user] = await db.select().from(usersTable).where(eq(usersTable.id, userId));
  if (!user) {
    res.status(404).json({ error: "User not found" });
    return;
  }

  const [policy] = await db
    .select()
    .from(policiesTable)
    .where(eq(policiesTable.userId, userId));

  const coverage = policy?.coverage ?? 50000;
  const fraudScore = computeFraudScore(userId, incomeImpact, triggerType);
  const trustScore = computeTrustScore(userId, fraudScore);
  const payout = computePayout(incomeImpact, fraudScore, coverage);
  const status = fraudScore > 70 ? "rejected" : fraudScore > 50 ? "under_review" : "approved";
  
  const explanation = TRIGGER_DESCRIPTIONS[triggerType] ??
    `${triggerType} event caused income disruption`;

  const claimId = randomUUID();

  await db.insert(claimsTable).values({
    id: claimId,
    userId,
    triggerType,
    incomeImpact,
    payout: status === "approved" ? payout : 0,
    status,
    fraudScore,
    explanation,
  });

  if (policy && status === "approved") {
    await db
      .update(policiesTable)
      .set({
        claimsCount: (policy.claimsCount ?? 0) + 1,
        totalPaidOut: (policy.totalPaidOut ?? 0) + payout,
      })
      .where(eq(policiesTable.id, policy.id));
  }

  req.log.info({ claimId, userId, status, payout }, "Claim processed");

  res.json(ProcessClaimResponse.parse({
    claimId,
    status,
    payout: status === "approved" ? payout : 0,
    fraudScore,
    trustScore,
    explanation,
    processingTime: "2.3 seconds",
  }));
});

router.get("/claims/:userId", async (req, res): Promise<void> => {
  const rawId = Array.isArray(req.params.userId) ? req.params.userId[0] : req.params.userId;
  const params = GetUserClaimsParams.safeParse({ userId: rawId });
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const claims = await db
    .select()
    .from(claimsTable)
    .where(eq(claimsTable.userId, params.data.userId))
    .orderBy(claimsTable.createdAt);

  const result = claims.map((c) => ({
    id: c.id,
    userId: c.userId,
    triggerType: c.triggerType,
    incomeImpact: c.incomeImpact,
    payout: c.payout,
    status: c.status,
    fraudScore: c.fraudScore,
    explanation: c.explanation,
    createdAt: c.createdAt.toISOString(),
  }));

  res.json(GetUserClaimsResponse.parse(result));
});

export default router;
