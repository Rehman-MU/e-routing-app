import os, requests, json, time
import streamlit as st
import pydeck as pdk

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="EV Routing Prototype", layout="wide")
st.title("🔌 EV Routing Prototype")

def typeahead(label):
    q = st.text_input(label)
    choice = None
    if len(q) >= 3:
        r = requests.get(f"{BACKEND}/api/v1/autocomplete", params={"q": q, "limit": 5}, timeout=10)
        opts = r.json()
        labels = [o["label"] for o in opts]
        idx = st.selectbox("Suggestions", range(len(labels)), format_func=lambda i: labels[i]) if labels else None
        if idx is not None:
            choice = opts[idx]
    return choice

col1, col2 = st.columns(2)
with col1:
    start = typeahead("Departure (type to search)")
with col2:
    end = typeahead("Arrival (type to search)")

with st.sidebar:
    st.header("Vehicle & SOC")
    # fetch demo vehicles
    # quick/dirty: these aren't exposed as an API; seed default IDs 1..5
    veh_id = st.selectbox("Vehicle ID", [1,2,3,4,5], index=0)
    start_soc = st.slider("Start SOC (%)", 1, 100, 80)
    arrival_soc = st.slider("Arrival SOC (%)", 0, 100, 20)

go = st.button("Plan Route")
if go:
    if not start or not end:
        st.warning("Please pick both start and end from suggestions.")
        st.stop()

    st.write("Routing & planning…")
    body = {
        "start": start["coord"], "end": end["coord"],
        "start_soc": start_soc, "arrival_soc": arrival_soc,
        "vehicle_id": veh_id
    }
    r = requests.post(f"{BACKEND}/api/v1/ev-plan", json=body, timeout=30)
    #  error handeling
    if r.status_code != 200:
        st.error(f"Backend error {r.status_code}:\n\n{r.text[:500]}")
        st.stop() 
    if not r.ok:
        st.error(f"Backend error {r.status_code}:\n\n{r.text[:800]}")
        st.stop()

    data = r.json()

    for label in ["fastest", "cheapest"]:
        st.subheader(label.capitalize())
        plan = data.get(label, {})
        summary = plan.get("summary", {})
        st.markdown(
            f"**Drive:** {summary.get('drive_min',0):.1f} min  •  "
            f"**Charge:** {summary.get('charge_min',0):.1f} min  •  "
            f"**Total:** {summary.get('total_time_min',0):.1f} min"
        )

        # Map
        route = plan.get("route", {})
        stops = plan.get("stops", [])

        layers = []
        if route and route.get("coordinates"):
            layers.append(
                pdk.Layer(
                    "PathLayer",
                    data=[{"path": route["coordinates"], "name": "route"}],
                    get_path="path",
                    width_scale=5, width_min_pixels=3,
                )
            )
        if stops:
            layers.append(
                pdk.Layer(
                    "ScatterplotLayer",
                    data=[{"position":[s["lon"], s["lat"]], "name": s.get("name","charger")} for s in stops],
                    get_position="position",
                    get_radius=200,
                )
            )
        center = route["coordinates"][len(route["coordinates"])//2] if route else start["coord"]
        st.pydeck_chart(pdk.Deck(
            initial_view_state=pdk.ViewState(latitude=center[1], longitude=center[0], zoom=7),
            layers=layers, map_style=None
        ))
