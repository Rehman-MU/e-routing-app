from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://evr:evrpass@db:5432/evr"
    OSRM_BASE_URL: str = "https://router.project-osrm.org"
    PHOTON_BASE_URL: str = "https://photon.komoot.io"
    OCM_BASE_URL: str = "https://api.openchargemap.io/v3/poi"
    OCM_API_KEY: str | None = None
    REDIS_URL: str | None = None
    APP_SECRET_KEY: str = "change-me"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
