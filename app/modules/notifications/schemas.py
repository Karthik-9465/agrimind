from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class NotificationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    message: str
    category: str
    channel: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class NotificationCreateRequest(BaseModel):
    title: str
    message: str
    category: str = "system"
    channel: str = "console_stub"
    user_id: Optional[str] = None

class NotificationListResponse(BaseModel):
    total: int
    unread_count: int
    notifications: List[NotificationResponse]
