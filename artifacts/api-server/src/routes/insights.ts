import { Router, type IRouter } from "express";
import { db, usersTable, claimsTable } from "@workspace/db";
import { eq } from "drizzle-orm";
import {
  GetUserInsightsParams,
  GetUserInsightsResponse,
  GetDashboardSummaryQueryParams,
  GetDashboardSummaryResponse,
} from "@workspace/api-zod";

const router: IRouter = Router();

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function generateWeeklyEarnings(income: number) {
  const dailyBase = income / 26;
  return DAYS.map((day) => {
    const isWeekend = day === "Sat" || day === "Sun";
    const multiplier = isWeekend ? 1.3 : 0.9 + Math.random() * 0.3;
    return {
      day,
      amount: Math.round(dailyBase * multiplier),
      hoursWorked: isWeekend ? 10 + Math.round(Math.random() * 3) : 8 + Math.round(Math.random() * 2),
    };
  });
}

router.get("/insights/:userId", async (req, res): Promise<void> => {
  const rawId = Array.isArray(req.params.userId) ? req.params.userId[0] : req.params.userId;
  const params = GetUserInsightsParams.safeParse({ userId: rawId });
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const [user] = await db.select().from(usersTable).where(eq(usersTable.id, params.data.userId));
  if (!user) {
    res.status(404).json({ error: "User not found" });
    return;
  }

  const weeklyEarnings = generateWeeklyEarnings(user.income);

  const earningTimes = ["Evening (6-10pm)", "Morning (6-10am)", "Lunch (12-2pm)"];
  const earningDays = ["Friday", "Saturday", "Thursday"];
  const riskFactors = [
    ["Rain", "Platform Outages", "Traffic"],
    ["AQI", "Heat Wave", "UPI Downtime"],
    ["Platform Outages", "Rain", "Competition"],
  ];

  const idx = user.income % 3;
  const performanceScore = Math.min(100, Math.round(85 + (user.riskScore < 50 ? 10 : -5) + Math.random() * 10));

  res.json(GetUserInsightsResponse.parse({
    userId: params.data.userId,
    bestEarningTime: earningTimes[idx % earningTimes.length] ?? earningTimes[0],
    bestEarningDay: earningDays[idx % earningDays.length] ?? earningDays[0],
    riskExposure: user.riskScore,
    performanceScore,
    weeklyEarnings,
    monthlyTrend: user.riskScore < 50 ? "improving" : user.riskScore > 70 ? "declining" : "stable",
    topRiskFactors: riskFactors[idx % riskFactors.length] ?? riskFactors[0],
    savingsRecommendation: Math.round(user.income * 0.12),
  }));
});

router.get("/dashboard/summary", async (req, res): Promise<void> => {
  const queryParams = GetDashboardSummaryQueryParams.safeParse(req.query);
  if (!queryParams.success) {
    res.status(400).json({ error: queryParams.error.message });
    return;
  }

  const { userId } = queryParams.data;
  const [user] = await db.select().from(usersTable).where(eq(usersTable.id, userId));
  if (!user) {
    res.status(404).json({ error: "User not found" });
    return;
  }

  const claims = await db.select().from(claimsTable).where(eq(claimsTable.userId, userId));
  const thisMonthClaims = claims.filter((c) => {
    const date = new Date(c.createdAt);
    const now = new Date();
    return date.getMonth() === now.getMonth() && date.getFullYear() === now.getFullYear();
  });

  const dailyBase = user.income / 26;
  const todayEarnings = Math.round(dailyBase * (0.85 + Math.random() * 0.3));
  const weeklyEarnings = Math.round(dailyBase * 6 * (0.9 + Math.random() * 0.2));
  const monthlyEarnings = Math.round(user.income * (0.88 + Math.random() * 0.15));
  const totalPayoutThisMonth = thisMonthClaims.reduce((sum, c) => sum + (c.payout ?? 0), 0);
  const incomeProtected = Math.round(user.income * 3);

  res.json(GetDashboardSummaryResponse.parse({
    userId,
    todayEarnings,
    weeklyEarnings,
    monthlyEarnings,
    currentRiskScore: user.riskScore,
    activePolicies: 1,
    totalClaimsThisMonth: thisMonthClaims.length,
    totalPayoutThisMonth,
    riskTrend: user.riskScore < 50 ? "improving" : user.riskScore > 70 ? "worsening" : "stable",
    incomeProtected,
    streakDays: Math.floor(Math.random() * 15) + 1,
  }));
});

export default router;
