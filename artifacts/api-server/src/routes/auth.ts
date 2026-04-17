import { Router, type IRouter } from "express";
import { db, usersTable, policiesTable } from "@workspace/db";
import { eq } from "drizzle-orm";
import { RegisterUserBody, ListUsersResponse } from "@workspace/api-zod";
import { randomUUID } from "crypto";

const router: IRouter = Router();

function computeRiskScore(income: number, workType: string, city: string): number {
  let base = 50;
  
  if (workType === "delivery") base += 15;
  else if (workType === "rideshare") base += 10;
  else if (workType === "construction") base += 20;
  else if (workType === "freelance") base -= 5;
  else if (workType === "domestic_help") base += 5;
  
  if (income < 15000) base += 15;
  else if (income < 25000) base += 5;
  else if (income > 50000) base -= 10;
  
  const highRiskCities = ["Mumbai", "Delhi", "Kolkata", "Chennai"];
  if (highRiskCities.includes(city)) base += 8;
  
  return Math.min(Math.max(Math.round(base + (Math.random() * 10 - 5)), 10), 95);
}

function computePremium(income: number, riskScore: number): number {
  const lossRatio = 0.065;
  const multiplier = riskScore > 70 ? 1.3 : riskScore > 50 ? 1.1 : 0.9;
  return Math.round((income * (riskScore / 100) * lossRatio * 7) * multiplier);
}

router.post("/register", async (req, res): Promise<void> => {
  const parsed = RegisterUserBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  const { name, city, income, workType } = parsed.data;
  const userId = randomUUID();
  const riskScore = computeRiskScore(income, workType, city);
  const premium = computePremium(income, riskScore);
  const coverage = Math.round(income * 3);

  await db.insert(usersTable).values({
    id: userId,
    name,
    city,
    income,
    workType,
    riskScore,
  });

  const policyId = randomUUID();
  const today = new Date();
  const nextMonth = new Date(today);
  nextMonth.setMonth(nextMonth.getMonth() + 1);

  await db.insert(policiesTable).values({
    id: policyId,
    userId,
    coverageType: riskScore > 70 ? "premium" : riskScore > 50 ? "standard" : "basic",
    premium,
    coverage,
    status: "active",
    startDate: today.toISOString().split("T")[0],
    nextPaymentDate: nextMonth.toISOString().split("T")[0],
    claimsCount: 0,
    totalPaidOut: 0,
  });

  req.log.info({ userId, riskScore }, "User registered");

  res.status(201).json({
    userId,
    name,
    city,
    riskScore,
    premium,
    coverage,
    message: `Welcome ${name}! Your income protection policy is active. Risk score: ${riskScore}/100`,
  });
});

router.get("/users", async (req, res): Promise<void> => {
  const users = await db.select().from(usersTable).orderBy(usersTable.createdAt);
  const result = users.map((u) => ({
    id: u.id,
    name: u.name,
    city: u.city,
    income: u.income,
    workType: u.workType,
    riskScore: u.riskScore,
    createdAt: u.createdAt.toISOString(),
  }));
  res.json(ListUsersResponse.parse(result));
});

export default router;
