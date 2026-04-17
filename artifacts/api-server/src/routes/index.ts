import { Router, type IRouter } from "express";
import healthRouter from "./health";
import authRouter from "./auth";
import policyRouter from "./policy";
import claimsRouter from "./claims";
import triggersRouter from "./triggers";
import simulationRouter from "./simulation";
import decisionsRouter from "./decisions";
import mapRouter from "./map";
import insightsRouter from "./insights";
import aiRouter from "./ai";

const router: IRouter = Router();

router.use(healthRouter);
router.use(authRouter);
router.use(policyRouter);
router.use(claimsRouter);
router.use(triggersRouter);
router.use(simulationRouter);
router.use(decisionsRouter);
router.use(mapRouter);
router.use(insightsRouter);
router.use(aiRouter);

export default router;
