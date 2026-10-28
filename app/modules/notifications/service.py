import logging
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from app.db.models import NotificationLog

logger = logging.getLogger("agrimind.notifications")

class NotificationService:

    @staticmethod
    def send_notification(
        db: Session,
        user_id: str,
        title: str,
        message: str,
        category: str = "weather_alert",
        channel: str = "console_stub"
    ) -> NotificationLog:
        """
        Creates a notification log entry in DB and executes console/email delivery stubs.
        """
        notification = NotificationLog(
            user_id=user_id,
            title=title,
            message=message,
            category=category,
            channel=channel,
            is_read=False
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        # Execution stub for delivery channel
        if channel == "email_stub":
            logger.info(f"[NOTIFICATION STUB - EMAIL SENT] To user_id={user_id} | Subject: {title} | Content: {message}")
            print(f"📧 [EMAIL STUB SENT] User: {user_id} | Title: '{title}' | Message: '{message}'")
        else:
            logger.info(f"[NOTIFICATION STUB - CONSOLE ALERT] To user_id={user_id} | Title: {title} | Content: {message}")
            print(f"🔔 [CONSOLE ALERT STUB] User: {user_id} | Title: '{title}' | Message: '{message}'")

        return notification

    @staticmethod
    def get_user_notifications(db: Session, user_id: str) -> Tuple[List[NotificationLog], int, int]:
        """
        Retrieves all notifications for a specific user.
        Returns (notifications, total_count, unread_count).
        """
        query = db.query(NotificationLog).filter(NotificationLog.user_id == user_id).order_by(NotificationLog.created_at.desc())
        notifications = query.all()
        total_count = len(notifications)
        unread_count = sum(1 for n in notifications if not n.is_read)
        return notifications, total_count, unread_count

    @staticmethod
    def mark_as_read(db: Session, notification_id: str, user_id: str) -> Optional[NotificationLog]:
        """
        Marks a specific notification as read.
        """
        notification = db.query(NotificationLog).filter(
            NotificationLog.id == notification_id,
            NotificationLog.user_id == user_id
        ).first()
        if notification:
            notification.is_read = True
            db.commit()
            db.refresh(notification)
        return notification

    @staticmethod
    def mark_all_as_read(db: Session, user_id: str) -> int:
        """
        Marks all unread notifications for a user as read.
        Returns number of updated notifications.
        """
        updated = db.query(NotificationLog).filter(
            NotificationLog.user_id == user_id,
            NotificationLog.is_read == False
        ).update({"is_read": True})
        db.commit()
        return updated
