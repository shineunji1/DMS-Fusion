from pydantic import BaseModel

class MonitoringStatus(BaseModel):
    status: str
