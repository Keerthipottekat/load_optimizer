"""
FastAPI backend for the AI-Driven Transformer Load Optimization System.

Provides a single `/simulate` endpoint that executes the existing
controller logic and returns JSON results suitable for a plain-JS frontend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/simulate")
def simulate():
    """Run a full 24‑hour simulation and return summarized results.

    The response contains a `history` list with one entry per hour and a
    `metrics` object that aggregates key statistics.
    """
    controller = SystemController(transformer_capacity=150.0, verbose=False)
    states = controller.execute_24h()

    history = []
    for s in states:
        optimized_load = (
            s.optimization_result.optimized_load
            if s.optimization_result and s.is_overloaded
            else s.total_current_load
        )
        logs = s.optimization_result.actions if s.optimization_result else []

        # convert numpy scalars to native types
        zone_allocs = {k: float(v) for k, v in s.current_loads.items()}

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
    metrics = {
        "peak_load": float(df["total_load"].max()),
        "min_load": float(df["total_load"].min()),
        "avg_load": float(df["total_load"].mean()),
        "total_shed": float((df["predicted_load"] - df["total_load"]).sum()),
        "overload_hours": int(df["is_overloaded"].sum()),
        "optimized_hours": int((df["total_load"] < df["predicted_load"]).sum()),
        "capacity": controller.capacity,
    }

    return {"history": history, "metrics": metrics}


# start the server with:
#    uvicorn backend.main:app --reload
