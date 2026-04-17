import { Router, type IRouter } from "express";
import { db, usersTable } from "@workspace/db";
import { eq } from "drizzle-orm";
import { GetDailyPlanParams, GetDailyPlanResponse } from "@workspace/api-zod";

const router: IRouter = Router();

router.get("/daily-plan/:userId", async (req, res): Promise<void> => {
  const rawId = Array.isArray(req.params.userId) ? req.params.userId[0] : req.params.userId;
  const params = GetDailyPlanParams.safeParse({ userId: rawId });
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const [user] = await db.select().from(usersTable).where(eq(usersTable.id, params.data.userId));
  if (!user) {
    res.status(404).json({ error: "User not found" });
    return;
  }

  const today = new Date();
  const dayOfWeek = today.getDay();
  const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;

  const baseEarning = user.income / 26;
  const modifier = isWeekend ? 1.35 : 1.0;

  const workWindows = [
    {
      startTime: "06:00",
      endTime: "10:00",
      demandScore: 85,
      estimatedEarning: Math.round(baseEarning * 0.35 * modifier),
      label: "Morning Peak",
    },
    {
      startTime: "12:00",
      endTime: "14:00",
      demandScore: 92,
      estimatedEarning: Math.round(baseEarning * 0.28 * modifier),
      label: "Lunch Rush",
    },
    {
      startTime: "18:00",
      endTime: "22:00",
      demandScore: 96,
      estimatedEarning: Math.round(baseEarning * 0.45 * modifier),
      label: "Evening Prime",
    },
  ];

  const highDemandZones = [
    {
      name: `${user.city} Central Business District`,
      demandScore: 94,
      avgEarning: Math.round(baseEarning * 0.18),
      distanceKm: 3.2,
    },
    {
      name: `${user.city} Tech Hub`,
      demandScore: 88,
      avgEarning: Math.round(baseEarning * 0.15),
      distanceKm: 6.8,
    },
    {
      name: `${user.city} Market Area`,
      demandScore: 82,
      avgEarning: Math.round(baseEarning * 0.12),
      distanceKm: 1.5,
    },
  ];

  const riskWindows = [
    {
      startTime: "08:00",
      endTime: "09:30",
      riskType: "Traffic Congestion",
      severity: "medium",
      advice: "Avoid major arterial roads. Use service lanes for 20% faster routes.",
    },
    {
      startTime: "12:30",
      endTime: "13:30",
      riskType: "Rain Risk",
      severity: "high",
      advice: "IMD forecast: 70% chance of heavy showers. Keep rain gear ready.",
    },
    {
      startTime: "19:00",
      endTime: "20:00",
      riskType: "Platform Load",
      severity: "low",
      advice: "High order volume may cause app lag. Pre-accept known routes.",
    },
  ];

  const expectedEarnings = workWindows.reduce((sum, w) => sum + w.estimatedEarning, 0);

  const weatherConditions = ["Partly Cloudy, 28°C", "Rain expected from 12pm", "Clear skies, 32°C"];
  const weatherForecast = weatherConditions[today.getDate() % 3];

  const tips = [
    "Lunch rush orders from IT parks pay 22% above average. Position near Sector 5 by 11:45am.",
    "Your acceptance rate is above 87% — eligible for priority dispatch queue.",
    "Weather alert: Rain at 1pm. Complete 2 extra deliveries before noon to offset risk.",
    "Friday evenings show your highest earnings — extend shift by 90 minutes for +₹180 average.",
  ];

  res.json(GetDailyPlanResponse.parse({
    userId: params.data.userId,
    date: today.toISOString().split("T")[0],
    bestWorkingHours: workWindows,
    highDemandZones,
    riskWindows,
    expectedEarnings,
    recommendation: `Focus on ${isWeekend ? "residential zones" : "business districts"} today. ${isWeekend ? "Weekend demand peaks at restaurants and malls." : "Weekday corporate lunch rush is your highest-value window."}`,
    weatherForecast: weatherForecast ?? "Clear, 30°C",
    topTip: tips[today.getDate() % tips.length] ?? tips[0],
  }));
});

export default router;
