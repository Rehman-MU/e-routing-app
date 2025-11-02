import os, requests
import streamlit as st
import pydeck as pdk

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="EV Routing Prototype", layout="wide")
st.title("🔌 EV Routing Prototype")

# ----------------------------
# Helpers
def typeahead(label: str):
    q = st.text_input(label)
    choice = None
    if len(q) >= 3:
        try:
            r = requests.get(
                f"{BACKEND}/api/v1/autocomplete",
                params={"q": q, "limit": 5}, 
                timeout=10
            )
            if r.ok:
                opts = r.json()
                labels = [o["label"] for o in opts]
                if labels:
                    idx = st.selectbox(
                        "Suggestions", 
                        range(len(labels)),
                        format_func=lambda i: labels[i],
                        key=f"suggestions_{label}"  # Unique key for each typeahead
                    )
                    if idx is not None:
                        choice = opts[idx]
            else:
                st.warning(f"Autocomplete error {r.status_code}: {r.text[:200]}")
        except requests.exceptions.ConnectionError:
            st.error(f"⚠️ Cannot connect to backend at {BACKEND}. Please check if the backend service is running.")
        except requests.exceptions.RequestException as e:
            st.warning(f"Network error: {e}")
    return choice

def make_route_layer(route_coords):
    return pdk.Layer(
        "PathLayer",
        data=[{"path": route_coords}],
        get_path="path",
        width_scale=2,
        width_min_pixels=3,
        pickable=False,
    )

def make_scatter_layer(points, radius=200, color=None, pickable=False, tooltip=False):
    # points: list of dicts with "position": [lon, lat], optional "name","minutes"
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=points,
        get_position="position",
        get_radius=radius,
        pickable=pickable,
        get_fill_color=color if color else [200, 200, 200, 160],
    )
    return layer

# ----------------------------
# UI
# ----------------------------
col1, col2 = st.columns(2)
with col1:
    start = typeahead("Departure (type to search)")
with col2:
    end = typeahead("Arrival (type to search)")

with st.sidebar:
    st.header("Vehicle & SOC")
    veh_id = st.selectbox("Vehicle ID", [1, 2, 3, 4, 5], index=0)
    start_soc = st.slider("Start SOC (%)", 1, 100, 80)
    arrival_soc = st.slider("Arrival SOC (%)", 0, 100, 20)

go = st.button("Plan Route")

# ----------------------------
# Plan + Map
# ----------------------------
if go:
    if not start or not end:
        st.warning("Please pick both start and end from suggestions.")
        st.stop()

    st.write("Routing & planning…")
    body = {
        "start": start["coord"],
        "end": end["coord"],
        "start_soc": start_soc,
        "arrival_soc": arrival_soc,
        "vehicle_id": veh_id,
    }
    r = requests.post(f"{BACKEND}/api/v1/ev-plan", json=body, timeout=30)

    # clearer error handling (prevents JSONDecodeError)
    if not r.ok:
        st.error(f"Backend error {r.status_code}:\n\n{r.text[:800]}")
        st.stop()

    data = r.json()

    for label in ["fastest", "cheapest"]:
        plan = data.get(label, {})
        summary = plan.get("summary", {})
        st.subheader(label.capitalize())
        st.markdown(
            f"**Drive:** {summary.get('drive_min', 0):.1f} min  •  "
            f"**Charge:** {summary.get('charge_min', 0):.1f} min  •  "
            f"**Total:** {summary.get('total_time_min', 0):.1f} min"
        )

        route = plan.get("route", {})
        coords = route.get("coordinates") or []
        stops = plan.get("stops", [])
        chargers = data.get("chargers", [])  # optional list from backend

        layers = []

        # Route polyline
        if coords:
            layers.append(make_route_layer(coords))

        # Start / End pins (green/red)
        if coords:
            layers.append(make_scatter_layer(
                [{"position": coords[0]}],
                radius=250,
                color=[20, 200, 90, 220],   # green
            ))
            layers.append(make_scatter_layer(
                [{"position": coords[-1]}],
                radius=250,
                color=[220, 50, 50, 220],   # red
            ))

        # All corridor chargers as small gray dots
        if chargers:
            layers.append(make_scatter_layer(
                [{"position": [c["lon"], c["lat"]]} for c in chargers],
                radius=80,
                color=[180, 180, 180, 160],
            ))

        # Selected charging stops: bigger + tooltip
        if stops:
            stop_points = [{"position": [s["lon"], s["lat"]],
                            "name": s.get("name", "Charger"),
                            "minutes": s.get("charge_min", 0)} for s in stops]
            layers.append(pdk.Layer(
                "ScatterplotLayer",
                data=stop_points,
                get_position="position",
                get_radius=220,
                pickable=True,
                get_fill_color=[255, 200, 60, 220],  # amber-ish
            ))
            tooltip = {"text": "{name}\n{minutes} min"}
        else:
            tooltip = None

        # Center map roughly on route midpoint or start
        center = coords[len(coords)//2] if coords else start["coord"]
        view = pdk.ViewState(latitude=center[1], longitude=center[0], zoom=6)

        st.pydeck_chart(pdk.Deck(
            initial_view_state=view,
            layers=layers,
            tooltip=tooltip,
            map_style=None
        ))
