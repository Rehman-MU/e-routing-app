import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="EV Route Planner",
    page_icon="⚡",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .route-card {
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #ddd;
        margin: 1rem 0;
    }
    .fastest-route {
        border-left: 5px solid #ff6b6b;
    }
    .cheapest-route {
        border-left: 5px solid #4ecdc4;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header"> Electric Vehicle Route Planner</h1>', unsafe_allow_html=True)

# Sidebar for input
with st.sidebar:
    st.header("Route Details")
    
    start_location = st.text_input("Starting Location", "Berlin, Germany")
    destination = st.text_input("Destination", "Hamburg, Germany")
    
    col1, col2 = st.columns(2)
    with col1:
        start_soc = st.slider("Starting SOC (%)", 0, 100, 80)
    with col2:
        arrival_soc = st.slider("Desired Arrival SOC (%)", 0, 100, 20)
    
    calculate_btn = st.button("Calculate Routes", type="primary")

# Main content
if calculate_btn:
    try:
        # Show loading spinner
        with st.spinner("Calculating optimal routes..."):
            # Call backend API
            backend_url = "http://backend:8000/api/v1/calculate-routes"
            payload = {
                "start_location": start_location,
                "destination": destination,
                "start_soc": start_soc,
                "arrival_soc": arrival_soc
            }
            
            response = requests.post(backend_url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                # Display results in two columns
                col1, col2 = st.columns(2)
                
                # Fastest Route
                with col1:
                    st.markdown('<div class="route-card fastest-route">', unsafe_allow_html=True)
                    st.subheader(" Fastest Route")
                    st.metric("Total Time", f"{data['total_fastest_time']:.1f} min")
                    st.metric("Total Cost", f"€{data['total_fastest_cost']:.2f}")
                    
                    st.write("### Route Steps:")
                    for i, step in enumerate(data['fastest_route'], 1):
                        st.write(f"{i}. {step['instruction']}")
                        if step['distance'] > 0:
                            st.write(f"    Distance: {step['distance']:.1f} km")
                        st.write(f"   Duration: {step['duration']:.1f} min")
                        if step['charge_time'] > 0:
                            st.write(f"   Charge Time: {step['charge_time']} min")
                        st.write("---")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Cheapest Route
                with col2:
                    st.markdown('<div class="route-card cheapest-route">', unsafe_allow_html=True)
                    st.subheader(" Cheapest Route")
                    st.metric("Total Time", f"{data['total_cheapest_time']:.1f} min")
                    st.metric("Total Cost", f"€{data['total_cheapest_cost']:.2f}")
                    
                    st.write("### Route Steps:")
                    for i, step in enumerate(data['cheapest_route'], 1):
                        st.write(f"{i}. {step['instruction']}")
                        if step['distance'] > 0:
                            st.write(f"    Distance: {step['distance']:.1f} km")
                        st.write(f"    Duration: {step['duration']:.1f} min")
                        if step['charge_time'] > 0:
                            st.write(f"    Charge Time: {step['charge_time']} min")
                        st.write("---")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Comparison chart
                st.subheader("Route Comparison")
                
                comparison_data = {
                    'Route Type': ['Fastest Route', 'Cheapest Route'],
                    'Time (min)': [data['total_fastest_time'], data['total_cheapest_time']],
                    'Cost (€)': [data['total_fastest_cost'], data['total_cheapest_cost']]
                }
                
                df = pd.DataFrame(comparison_data)
                
                col1, col2 = st.columns(2)
                with col1:
                    fig_time = px.bar(df, x='Route Type', y='Time (min)', 
                                    title='Time Comparison', color='Route Type')
                    st.plotly_chart(fig_time, use_container_width=True)
                
                with col2:
                    fig_cost = px.bar(df, x='Route Type', y='Cost (€)', 
                                    title='Cost Comparison', color='Route Type')
                    st.plotly_chart(fig_cost, use_container_width=True)
                    
            else:
                st.error("Error calculating routes. Please try again.")
                
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to the backend service. Please make sure the backend is running.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

else:
    # Welcome message
    st.markdown("""
    ## Welcome to EV Route Planner! 
    
    This app helps you find the **fastest** and **cheapest** routes for your electric vehicle journey.
    
    ### How to use:
    1. Enter your starting location and destination
    2. Set your starting State of Charge (SOC)
    3. Set your desired arrival SOC
    4. Click "Calculate Routes"
    
    ### Features:
    - Electric vehicle optimized routing
    - Charging station consideration
    - Time and cost calculations
    - Route comparison
    
    *Note: This is a learning prototype using mock data.*
    """)
    
    # Sample image placeholder
    st.image("https://via.placeholder.com/800x400/4ECDC4/FFFFFF?text=EV+Route+Planner", 
             caption="Electric Vehicle Routing Visualization", use_column_width=True)