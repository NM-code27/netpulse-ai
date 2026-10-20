from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (routes_alerts, routes_assistant, routes_evaluation,
                      routes_metrics, routes_realworld, routes_scenario, routes_topology)
from app.config import settings
from app.db.init_db import init_db
from app.worker import run_scoring, run_tick

app = FastAPI(title="NetPulse AI", description="Predictive network observability and root-cause intelligence")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_topology.router)
app.include_router(routes_metrics.router)
app.include_router(routes_alerts.router)
app.include_router(routes_scenario.router)
app.include_router(routes_assistant.router)
app.include_router(routes_evaluation.router)
app.include_router(routes_realworld.router)

scheduler = BackgroundScheduler()


@app.on_event("startup")
def on_startup():
    init_db()
    scheduler.add_job(run_tick, "interval", seconds=settings.simulator_tick_seconds, id="sim_tick",
                       max_instances=1, coalesce=True)
    scheduler.add_job(run_scoring, "interval", seconds=settings.scoring_interval_seconds, id="scoring",
                       max_instances=1, coalesce=True)
    scheduler.start()


@app.on_event("shutdown")
def on_shutdown():
    scheduler.shutdown(wait=False)


@app.get("/")
def health():
    return {"status": "ok", "service": "netpulse-ai-backend"}
