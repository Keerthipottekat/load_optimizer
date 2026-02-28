"""
FastAPI backend for the AI-Driven Transformer Load Optimization System.

Provides a single `/simulate` endpoint that executes the existing
controller logic and returns JSON results suitable for a plain-JS frontend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List

from backend.controller import SystemController


app = FastAPI(title="Transformer Load Optimization API")

# enable CORS so that the frontend (served separately) can call us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Request model for /recommend-schedule ----

class ScheduleRequest(BaseModel):
    """Request body for the load shedding schedule endpoint."""
    scenario: str = Field(default="normal", description="Demand scenario")
    capacity: float = Field(default=150.0, description="Transformer capacity")
    protected_zones: List[str] = Field(
        default=["hospital"],
        description="Zones that must never be shed",
    )
    max_outage_hours_per_zone: int = Field(
        default=2,
        description="Max hours any single zone may be shed",
    )


@app.get("/simulate")
def simulate(scenario: str = "normal", algorithm: str = "proportional"):
    """Run a full 24‑hour simulation with optional scenario.

    Args:
        scenario: One of "normal", "heatwave", "high_ev", "emergency" (default: "normal")
        algorithm: 'proportional' or 'greedy'

    The response contains a `history` list with one entry per hour and a
    `metrics` object that aggregates key statistics.
    """
    # instantiate controller
    controller = SystemController(
        transformer_capacity=150.0,
        verbose=False,
        algorithm=algorithm,
    )
    # regenerate demand profile (scenario may modify distribution)
    controller.demand_profile = controller.simulator.generate_24h_profile(scenario=scenario)
    controller.predictor.train(controller.demand_profile)
    states = controller.execute_24h()

    history = []
    for s in states:
        optimized_load = (
            s.optimization_result.optimized_load
            if s.optimization_result and s.is_overloaded
            else s.total_current_load
        )
        logs = s.optimization_result.actions if s.optimization_result else []

        # convert numpy scalars to native types, using optimized loads if available
        if s.optimization_result and s.is_overloaded:
            raw_allocs = s.optimization_result.optimized_loads
        else:
            raw_allocs = s.current_loads
            
        zone_allocs = {k: float(v) for k, v in raw_allocs.items()}

        history.append(
            {
                "hour": int(s.hour),
                "current_load": float(s.total_current_load),
                "predicted_load": float(s.predicted_load),
                "is_overloaded": bool(s.is_overloaded),
                "optimized_load": float(optimized_load),
                "zone_allocations": zone_allocs,
                "logs": logs,
            }
        )

    df = controller.get_state_history_dataframe()
    
    # Calculate Resilience Score and Blackout Risk Index
    base_capacity = controller.capacity
    max_ratio = (df["predicted_load"] / base_capacity).max()
    
    if max_ratio < 1.15:
        blackout_risk = "LOW"
    elif max_ratio < 1.25:
        blackout_risk = "MEDIUM"
    else:
        blackout_risk = "HIGH"
        
    overload_hours = int(df["is_overloaded"].sum())
    # Use post-optimization total_load instead of pre-optimization predicted_load for a fairer grade
    stress_ratio_sum = (df["total_load"] / base_capacity).sum()
    
    # Gentler penalty weights so the score doesn't default to 0% linearly
    resilience_score = 100 - (overload_hours * 2) - (stress_ratio_sum * 1.5)
    resilience_score = max(0, min(100, round(resilience_score, 2)))

    metrics = {
        "peak_load": float(df["total_load"].max()),
        "min_load": float(df["total_load"].min()),
        "avg_load": float(df["total_load"].mean()),
        "total_shed": float((df["predicted_load"] - df["total_load"]).sum()),
        "overload_hours": overload_hours,
        "optimized_hours": int((df["total_load"] < df["predicted_load"]).sum()),
        "capacity": base_capacity,
        "resilience_score": resilience_score,
        "blackout_risk": blackout_risk
    }

    return {"history": history, "metrics": metrics}


@app.post("/recommend-schedule")
def recommend_schedule(req: ScheduleRequest):
    """Generate an AI-assisted 24-hour load shedding schedule.

    Predicts overload per hour and automatically decides which zones to
    shed while respecting protected zones and maximum outage constraints.
    """
    controller = SystemController(
        transformer_capacity=req.capacity,
        verbose=False,
    )
    return controller.recommend_schedule(
        scenario=req.scenario,
        capacity=req.capacity,
        protected_zones=req.protected_zones,
        max_outage_hours_per_zone=req.max_outage_hours_per_zone,
    )


# start the server with:
#    uvicorn backend.main:app --reload
