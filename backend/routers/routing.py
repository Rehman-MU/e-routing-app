from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import requests
import math

router = APIRouter()

class RoutingRequest(BaseModel):
    start_location: str
    destination: str
    start_soc: float
    arrival_soc: float

class RouteStep(BaseModel):
    instruction: str
    distance: float
    duration: float
    charge_time: float = 0

class RoutingResponse(BaseModel):
    fastest_route: list[RouteStep]
    cheapest_route: list[RouteStep]
    total_fastest_time: float
    total_cheapest_time: float
    total_fastest_cost: float
    total_cheapest_cost: float

# Mock data for demonstration
MOCK_CHARGING_STATIONS = [
    {"name": "Station A", "location": "Midpoint 1", "cost_per_kwh": 0.30, "charging_speed": 50},
    {"name": "Station B", "location": "Midpoint 2", "cost_per_kwh": 0.25, "charging_speed": 30},
]

def calculate_distance(origin, destination):
    """Calculate distance between two points (simplified)"""
    # In real implementation, you'd use OSRM or Google Maps API
    return 100  # km

def get_route_from_osrm(start, end):
    """Get route from OSRM API"""
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{start};{end}?overview=false"
        response = requests.get(url)
        data = response.json()
        
        if data['code'] == 'Ok':
            route = data['routes'][0]
            return {
                'distance': route['distance'] / 1000,  # Convert to km
                'duration': route['duration'] / 60,    # Convert to minutes
                'steps': []
            }
    except:
        pass
    
    # Fallback mock data
    return {
        'distance': calculate_distance(start, end),
        'duration': calculate_distance(start, end) * 1.5,  # 1.5 min per km
        'steps': []
    }

@router.post("/calculate-routes", response_model=RoutingResponse)
async def calculate_routes(request: RoutingRequest):
    try:
        # Get base route
        base_route = get_route_from_osrm(request.start_location, request.destination)
        
        # EV parameters (mock values)
        battery_capacity = 60  # kWh
        consumption_rate = 0.2  # kWh per km
        max_range = battery_capacity / consumption_rate
        
        # Calculate if charging is needed
        required_range = base_route['distance']
        available_range = (request.start_soc / 100) * max_range
        
        if available_range >= required_range:
            # No charging needed
            fastest_route = [
                RouteStep(
                    instruction=f"Drive from {request.start_location} to {request.destination}",
                    distance=base_route['distance'],
                    duration=base_route['duration']
                )
            ]
            
            cheapest_route = fastest_route.copy()
            
            return RoutingResponse(
                fastest_route=fastest_route,
                cheapest_route=cheapest_route,
                total_fastest_time=base_route['duration'],
                total_cheapest_time=base_route['duration'],
                total_fastest_cost=0,
                total_cheapest_cost=0
            )
        else:
            # Charging needed - create mock charging stops
            fastest_steps = [
                RouteStep(
                    instruction=f"Drive from {request.start_location} to {MOCK_CHARGING_STATIONS[0]['name']}",
                    distance=base_route['distance'] * 0.4,
                    duration=base_route['duration'] * 0.4
                ),
                RouteStep(
                    instruction=f"Charge at {MOCK_CHARGING_STATIONS[0]['name']}",
                    distance=0,
                    duration=30,  # 30 minutes charging
                    charge_time=30
                ),
                RouteStep(
                    instruction=f"Drive from {MOCK_CHARGING_STATIONS[0]['name']} to {request.destination}",
                    distance=base_route['distance'] * 0.6,
                    duration=base_route['duration'] * 0.6
                )
            ]
            
            cheapest_steps = [
                RouteStep(
                    instruction=f"Drive from {request.start_location} to {MOCK_CHARGING_STATIONS[1]['name']}",
                    distance=base_route['distance'] * 0.5,
                    duration=base_route['duration'] * 0.5
                ),
                RouteStep(
                    instruction=f"Charge at {MOCK_CHARGING_STATIONS[1]['name']}",
                    distance=0,
                    duration=45,  # 45 minutes charging (slower but cheaper)
                    charge_time=45
                ),
                RouteStep(
                    instruction=f"Drive from {MOCK_CHARGING_STATIONS[1]['name']} to {request.destination}",
                    distance=base_route['distance'] * 0.5,
                    duration=base_route['duration'] * 0.5
                )
            ]
            
            # Calculate costs (simplified)
            energy_used_fastest = base_route['distance'] * consumption_rate
            charging_cost_fastest = 10 * MOCK_CHARGING_STATIONS[0]['cost_per_kwh']  # 10 kWh
            
            energy_used_cheapest = base_route['distance'] * consumption_rate
            charging_cost_cheapest = 10 * MOCK_CHARGING_STATIONS[1]['cost_per_kwh']  # 10 kWh
            
            return RoutingResponse(
                fastest_route=fastest_steps,
                cheapest_route=cheapest_steps,
                total_fastest_time=sum(step.duration for step in fastest_steps),
                total_cheapest_time=sum(step.duration for step in cheapest_steps),
                total_fastest_cost=charging_cost_fastest,
                total_cheapest_cost=charging_cost_cheapest
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating routes: {str(e)}")