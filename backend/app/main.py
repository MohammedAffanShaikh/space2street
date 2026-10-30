from __future__ import annotations

from math import hypot
from typing import Literal

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="AMINA Lunar Intelligence API", version="0.1.0", description="Research prototype; demo terrain is simulated.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class AnalyzeRequest(BaseModel):
    region: str = "Demo South Polar Test Region"
    elevation_m: list[list[float]]
    grid_spacing_m: float = Field(default=100.0, gt=0)
    source_name: str = "User supplied elevation grid"
    product_id: str = "unspecified"
    data_kind: Literal["measured", "demo"] = "measured"

class PlanRequest(BaseModel):
    terrain: list[list[float]]
    start: list[int] = [1, 1]
    goal: list[int] = [10, 10]
    grid_spacing_m: float = 100.0
    max_slope_deg: float = 18.0
    blocked: list[list[int]] = []
    energy_budget_wh: float = 220.0
    comms_available: bool = True

def demo_grid() -> np.ndarray:
    y, x = np.mgrid[0:24, 0:24]
    # Gently varying synthetic relief keeps the demo rover traverseable at 100 m/cell.
    z = 45 * np.sin(x / 4.6) + 35 * np.cos(y / 5.3) + 18 * np.sin((x + y) / 3.2)
    z += 65 * np.exp(-((x - 16) ** 2 + (y - 8) ** 2) / 18)
    return z.astype(float)

def analyze_grid(a: np.ndarray, spacing: float) -> dict:
    if a.ndim != 2 or min(a.shape) < 3 or not np.isfinite(a).all():
        raise HTTPException(422, "elevation_m must be a finite rectangular grid at least 3×3")
    gy, gx = np.gradient(a, spacing)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    suitability = np.clip(100 - slope * 3.6, 0, 100)
    return {"shape": list(a.shape), "elevation_range_m": [round(float(a.min()), 2), round(float(a.max()), 2)],
            "slope_deg": np.round(slope, 2).tolist(), "mean_slope_deg": round(float(slope.mean()), 2),
            "max_slope_deg": round(float(slope.max()), 2), "suitability": np.round(suitability, 1).tolist(),
            "mean_suitability": round(float(suitability.mean()), 1),
            "terrain_class": "derived from supplied elevation grid"}

def route(a: np.ndarray, start: tuple[int, int], goal: tuple[int, int], spacing: float, max_slope: float, blocked: set[tuple[int,int]]) -> list[list[int]]:
    rows, cols = a.shape
    for p in (start, goal):
        if not (0 <= p[0] < rows and 0 <= p[1] < cols): raise HTTPException(422, "start/goal outside grid")
    gy, gx = np.gradient(a, spacing)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    frontier = [(0.0, start)]; cost = {start: 0.0}; prev = {}
    import heapq
    while frontier:
        _, p = heapq.heappop(frontier)
        if p == goal: break
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                q = (p[0]+dr,p[1]+dc)
                if (dr == dc == 0 or not (0 <= q[0] < rows and 0 <= q[1] < cols) or q in blocked or slope[q] > max_slope): continue
                step = spacing * (1.4142 if dr and dc else 1) * (1 + slope[q]/max(max_slope,1)*2.5)
                nc = cost[p] + step
                if nc < cost.get(q, float("inf")):
                    cost[q]=nc; prev[q]=p
                    heuristic = hypot(goal[0]-q[0], goal[1]-q[1])*spacing
                    heapq.heappush(frontier,(nc+heuristic,q))
    if goal not in cost: return []
    path=[goal]
    while path[-1] != start: path.append(prev[path[-1]])
    return [[r,c] for r,c in reversed(path)]

CATALOG = [
    {"name":"LOLA Gridded Data Records (GDR)","instrument":"LRO LOLA","kind":"measured source","resolution":"Product-specific gridded maps","url":"https://pds-geosciences.wustl.edu/missions/lro/lola.htm","status":"available from source; not locally ingested"},
    {"name":"Diviner Derived and Calibrated Products","instrument":"LRO Diviner","kind":"measured source","resolution":"Varies by product; archive overview describes ~500 m horizontal scale","url":"https://pds-geosciences.wustl.edu/missions/lro/diviner.htm","status":"available from source; not locally ingested"},
    {"name":"LROC NAC/WAC Archive","instrument":"LRO Camera","kind":"measured source","resolution":"Product-specific; NAC can reach sub-meter scales","url":"https://pds-imaging.jpl.nasa.gov/documentation/LRO_ARCHSIS.PDF","status":"available from source; not locally ingested"},
]

@app.get("/api/health")
def health(): return {"status":"ok","mode":"demo-capable","api_version":"0.1.0"}

@app.get("/api/catalog")
def catalog(): return {"sources":CATALOG,"active_data":{"kind":"simulated","label":"Illustrative synthetic terrain grid"}}

@app.get("/api/demo/terrain")
def demo_terrain():
    a=demo_grid(); result=analyze_grid(a,100)
    return {"region":"AMINA Demo South Polar Test Region","data_kind":"simulated","source_name":"AMINA deterministic synthetic terrain generator","product_id":"demo-grid-v1","grid_spacing_m":100,"elevation_m":np.round(a,2).tolist(),**result}

@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    result=analyze_grid(np.array(req.elevation_m,dtype=float),req.grid_spacing_m)
    return {"region":req.region,"data_kind":req.data_kind,"source_name":req.source_name,"product_id":req.product_id,"grid_spacing_m":req.grid_spacing_m,**result,
            "resource_prospecting":{"score":None,"status":"not assessed","reason":"No PSR mask, thermal, radar, or compositional evidence supplied. Terrain alone cannot establish water ice."}}

@app.post("/api/plan")
def plan(req: PlanRequest):
    a=np.array(req.terrain,dtype=float)
    if a.ndim != 2 or min(a.shape)<3 or not np.isfinite(a).all(): raise HTTPException(422,"terrain must be a finite grid at least 3×3")
    path=route(a,tuple(req.start),tuple(req.goal),req.grid_spacing_m,req.max_slope_deg,{tuple(x) for x in req.blocked})
    distance=0.0
    for p,q in zip(path,path[1:]): distance += req.grid_spacing_m*hypot(p[0]-q[0],p[1]-q[1])
    full_distance=distance
    full_energy=full_distance*0.12
    goal_reached=bool(path) and path[-1] == req.goal
    if path and full_energy > req.energy_budget_wh:
        reachable=[path[0]]; distance=0.0; max_distance=req.energy_budget_wh/0.12
        for p,q in zip(path,path[1:]):
            step=req.grid_spacing_m*hypot(p[0]-q[0],p[1]-q[1])
            if distance+step > max_distance: break
            distance+=step; reachable.append(q)
        path=reachable; goal_reached=path[-1] == req.goal
    energy=distance*0.12
    feasible=goal_reached and energy <= req.energy_budget_wh
    status="planned" if feasible else ("energy-limited: safe waypoint reached; goal not reached" if path and full_energy > req.energy_budget_wh else ("no traversable route" if not path else "goal not reached"))
    return {"path":path,"distance_m":round(distance,1),"estimated_energy_wh":round(energy,1),"full_route_distance_m":round(full_distance,1),"full_route_energy_wh":round(full_energy,1),"energy_budget_wh":req.energy_budget_wh,"feasible":feasible,"goal_reached":goal_reached,"comms_available":req.comms_available,
            "status":status,"data_kind":"simulated route and energy estimate"}

@app.post("/api/mission/run")
def mission(req: PlanRequest):
    base=plan(req)
    baseline_req=req.model_copy(update={"blocked":[],"energy_budget_wh":max(req.energy_budget_wh,100000.0)})
    original=plan(baseline_req)
    agents=[
        {"agent":"Geospatial Analysis","finding":f"Computed slope field for {len(req.terrain)}×{len(req.terrain[0])} supplied cells."},
        {"agent":"Resource Prospecting","finding":"Ice evidence unavailable: no PSR, thermal, radar, or composition layers were supplied."},
        {"agent":"Terrain Safety","finding":f"Route constrained to cells at or below {req.max_slope_deg:.1f}° slope."},
        {"agent":"Energy and Communication","finding":f"Estimated {base['estimated_energy_wh']:.1f} Wh of {req.energy_budget_wh:.1f} Wh; communications {'available' if req.comms_available else 'interrupted (simulated)'}"},
        {"agent":"Mission Planning","finding":f"{len(base['path'])} route waypoints; {base['status']}."},
        {"agent":"Mission Commander","finding":"Decision assembled from computed tool outputs; evidence gaps retained."},
    ]
    decision="Proceed with simulated traverse" if base["feasible"] else ("Stop at the reachable waypoint; objective remains incomplete" if base["status"].startswith("energy-limited") else "Review route or terrain constraints")
    comparison={"original_path":original["path"],"revised_path":base["path"],"route_changed":original["path"]!=base["path"],"original_distance_m":original["distance_m"],"revised_distance_m":base["distance_m"],"original_energy_wh":original["estimated_energy_wh"],"revised_energy_wh":base["estimated_energy_wh"]}
    explanation="The route minimizes a slope-weighted grid cost while avoiding blocked and over-limit cells. An energy shortfall limits travel to the furthest reachable route waypoint and leaves the target incomplete. This is not a validated flight or rover plan."
    return {"plan":base,"original_plan":original,"route_comparison":comparison,"agent_outputs":agents,"decision":decision,"explanation":explanation,"evidence_status":"demo terrain; simulated route; no water-ice claim"}
