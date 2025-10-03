from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import routing

app = FastAPI(title="EV Routing API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routing.router, prefix="/api/v1", tags=["routing"])

@app.get("/")
async def root():
    return {"message": "EV Routing API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)