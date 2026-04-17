import { Router, type IRouter } from "express";
import { db, usersTable } from "@workspace/db";
import { eq } from "drizzle-orm";
import { SimulateScenarioQueryParams, SimulateScenarioResponse } from "@workspace/api-zod";

const router: IRouter = Router();

interface ScenarioConfig {
  riskPercent: number;
  incomeDropPercent: number;
  recommendedAction: string;
  explanation: string;
  expectedPayoutPercent: number;
  confidence: number;
}

const SCENARIO_CONFIGS: Record<string, ScenarioConfig> = {
  rain: {
    riskPercent: 65,
    incomeDropPercent: 40,
    recommendedAction: "File income protection claim. Switch to Instamart grocery deliveries — demand spikes 3x during rain.",
    explanation: "Rain probability 65% → causes 40% income drop historically. Heavy rainfall reduces delivery acceptance and slows commutes by 2.5x. Peak surge pricing on Uber/Ola can offset 15%.",
    expectedPayoutPercent: 35,
    confidence: 82,
  },
  location_change: {
    riskPercent: 20,
    incomeDropPercent: -15,
    recommendedAction: "Move to the recommended zone. High-density residential areas show 2.3x better earnings.",
    explanation: "Location change to high-demand zone historically increases earnings by 15-30%. Corporate areas on weekdays and markets on weekends show strongest demand.",
    expectedPayoutPercent: 0,
    confidence: 74,
  },
  skip_work: {
    riskPercent: 10,
    incomeDropPercent: 100,
    recommendedAction: "Activate income buffer. Your coverage provides 3 days of income protection for planned rest days.",
    explanation: "Skipping work triggers income gap protection if you have active policy. Historical data: 2 rest days per week optimal for long-term performance without burnout.",
    expectedPayoutPercent: 45,
    confidence: 95,
  },
  platform_outage: {
    riskPercent: 80,
    incomeDropPercent: 55,
    recommendedAction: "Switch platform immediately. Use Rapido or Dunzo as fallback. File emergency claim for verified outage.",
    explanation: "Platform outages cause 55% average income drop. Historical data shows 4-hour average outage duration. Zero-touch claim is auto-approved for verified platform incidents.",
    expectedPayoutPercent: 50,
    confidence: 91,
  },
  aqi_spike: {
    riskPercent: 55,
    incomeDropPercent: 28,
    recommendedAction: "Reduce outdoor hours. Morning slots (6-9am) have 40% lower AQI. N95 mask eligible for expense claim.",
    explanation: "AQI above 200 reduces worker availability by 35%. Health-conscious riders exit market — remaining workers earn 20% more per hour but at health cost.",
    expectedPayoutPercent: 25,
    confidence: 68,
  },
  heat_wave: {
    riskPercent: 45,
    incomeDropPercent: 22,
    recommendedAction: "Shift to morning (6-10am) and evening (6-9pm) slots. Avoid 12pm-5pm peak heat. Hydration expense claimable.",
    explanation: "Heat wave reduces peak-hour earning capacity. Early and late shifts show 30% higher efficiency. Food delivery demand stays high — opportunities exist for adaptive schedules.",
    expectedPayoutPercent: 18,
    confidence: 72,
  },
  upi_downtime: {
    riskPercent: 35,
    incomeDropPercent: 30,
    recommendedAction: "Accept cash orders only. Notify customers at pickup. UPI downtime typically resolves within 2-3 hours.",
    explanation: "UPI downtime affects payment collection but not order volume. Cash mode reduces conversion by 30%. NPCI historically resolves issues within 2.5 hours on average.",
    expectedPayoutPercent: 28,
    confidence: 78,
  },
};

router.get("/simulate", async (req, res): Promise<void> => {
  const params = SimulateScenarioQueryParams.safeParse(req.query);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const { scenario, userId } = params.data;

  let baseIncome = 25000;
  if (userId) {
    const [user] = await db.select().from(usersTable).where(eq(usersTable.id, userId));
    if (user) {
      baseIncome = user.income;
    }
  }

  const config = SCENARIO_CONFIGS[scenario] ?? SCENARIO_CONFIGS.rain;
  
  const incomeDrop = Math.round(baseIncome * (config.incomeDropPercent / 100));
  const predictedIncome = Math.max(0, Math.round(baseIncome - incomeDrop));
  const expectedPayout = Math.round(incomeDrop * (config.expectedPayoutPercent / 100));

  const alternativeScenarios = [
    {
      name: "Switch to morning shift (6-10am)",
      incomeChange: Math.round(baseIncome * 0.15),
      action: "Early deliveries have 40% less traffic and 20% higher surge pricing",
    },
    {
      name: "Move to Zone A (High Demand)",
      incomeChange: Math.round(baseIncome * 0.22),
      action: "Corporate areas show 2.3x demand multiplier on weekdays",
    },
    {
      name: "Accept surge pricing orders only",
      incomeChange: Math.round(baseIncome * 0.08),
      action: "Filter for 1.5x+ surge — fewer trips but higher per-trip income",
    },
  ];

  res.json(SimulateScenarioResponse.parse({
    scenario,
    predictedIncome,
    baseIncome,
    riskPercent: config.riskPercent,
    incomeDrop: Math.abs(incomeDrop),
    incomeDropPercent: Math.abs(config.incomeDropPercent),
    recommendedAction: config.recommendedAction,
    expectedPayout,
    explanation: config.explanation,
    confidence: config.confidence,
    alternativeScenarios,
  }));
});

export default router;
