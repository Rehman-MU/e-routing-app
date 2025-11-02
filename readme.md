# EV Routing System

A comprehensive Electric Vehicle routing system that calculates optimal routes with charging stops based on vehicle specifications and battery state of charge.

## Features

- **Route Planning**: Calculate fastest and cheapest routes for EVs
- **Charging Station Integration**: Find charging stations along the route using OpenChargeMap API
- **Vehicle Management**: Support for multiple EV models with different battery specifications
- **Real-time Autocomplete**: Location search using Photon geocoding service
- **Interactive Map**: Visualize routes and charging stops with PyDeck

## Technology Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: Streamlit, PyDeck
- **APIs**: OSRM (routing), Photon (geocoding), OpenChargeMap (charging stations)
- **Containerization**: Docker, Docker Compose

## Quick Start

### Prerequisites
- Docker and Docker Compose
- OpenChargeMap API key (optional)

### Installation

# 1. Clone the repository:
  https://github.com/Rehman-MU/e-routing-app.git
# 2. Edit .env with your configurations
  cp .env.example .env

# 3. run the application

  docker-compose up --build