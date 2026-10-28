from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User
from app.modules.auth.router import get_current_user
from app.modules.notifications.schemas import (
    NotificationResponse, NotificationCreateRequest, NotificationListResponse
)
from app.modules.notifications.service import NotificationService

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])

@router.get("/", response_model=NotificationListResponse)
def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve notification log history for the authenticated farmer.
    """
    items, total, unread = NotificationService.get_user_notifications(db, current_user.id)
    return NotificationListResponse(
        total=total,
        unread_count=unread,
        notifications=[NotificationResponse.model_validate(n) for n in items]
    )

@router.post("/trigger", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
def trigger_manual_notification(
    payload: NotificationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger an alert notification (weather alert, irrigation reminder, mandi price update).
    Uses console/email stubs.
    """
    target_user_id = payload.user_id if payload.user_id else current_user.id
    notification = NotificationService.send_notification(
        db=db,
        user_id=target_user_id,
        title=payload.title,
        message=payload.message,
        category=payload.category,
        channel=payload.channel
    )
    return NotificationResponse.model_validate(notification)

@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a specific notification as read.
    """
    notification = NotificationService.mark_as_read(db, notification_id, current_user.id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or access denied."
        )
    return NotificationResponse.model_validate(notification)

@router.patch("/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark all notifications for current user as read.
    """
    count = NotificationService.mark_all_as_read(db, current_user.id)
    return {"status": "success", "updated_count": count}
