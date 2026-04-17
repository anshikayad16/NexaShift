import { Router, type IRouter } from "express";
import { GetTriggersResponse } from "@workspace/api-zod";

const router: IRouter = Router();

const ALL_TRIGGERS = [
  {
    type: "rain",
    severity: "high",
    description: "Heavy rainfall warning: IMD has issued heavy rain alert for 6+ cities. Expected to reduce delivery income by 35-45%.",
    incomeImpactPercent: 40,
    cities: ["Mumbai", "Pune", "Bengaluru", "Hyderabad"],
    isActive: true,
  },
  {
    type: "aqi",
    severity: "medium",
    description: "Poor air quality: AQI levels above 200 in northern cities. Health advisory issued for outdoor workers.",
    incomeImpactPercent: 25,
    cities: ["Delhi", "Noida", "Gurugram", "Faridabad"],
    isActive: false,
  },
  {
    type: "heat",
    severity: "low",
    description: "Heat wave alert: Temperatures above 42°C expected between 12pm-5pm. Work advisories issued.",
    incomeImpactPercent: 20,
    cities: ["Rajasthan", "Delhi", "Ahmedabad"],
    isActive: false,
  },
  {
    type: "platform_outage",
    severity: "critical",
    description: "Zomato/Swiggy platform degradation: API gateway experiencing 60% error rate. Deliveries halted.",
    incomeImpactPercent: 60,
    cities: ["All cities"],
    isActive: false,
  },
  {
    type: "upi_downtime",
    severity: "medium",
    description: "NPCI reports partial UPI downtime affecting payment collections on gig platforms.",
    incomeImpactPercent: 30,
    cities: ["All cities"],
    isActive: false,
  },
];

router.get("/triggers", async (req, res): Promise<void> => {
  const activeTriggers = ALL_TRIGGERS.filter((t) => t.isActive);
  const maxSeverity = activeTriggers.length === 0 ? "low"
    : activeTriggers.some((t) => t.severity === "critical") ? "critical"
    : activeTriggers.some((t) => t.severity === "high") ? "high"
    : activeTriggers.some((t) => t.severity === "medium") ? "medium"
    : "low";

  const affectedCities = [...new Set(activeTriggers.flatMap((t) => t.cities))];

  res.json(GetTriggersResponse.parse({
    activeTriggers,
    riskLevel: maxSeverity,
    affectedCities,
  }));
});

export default router;
