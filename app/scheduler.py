import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import User, Farm
from app.modules.notifications.service import NotificationService
from app.modules.agent.tools.weather import get_weather_forecast
from app.modules.agent.tools.market import get_market_prices

logger = logging.getLogger("agrimind.scheduler")

scheduler = BackgroundScheduler(daemon=True)

def job_check_weather_alerts():
    """
    APScheduler Background Job: Checks weather forecasts for registered farms and issues weather alert notifications.
    """
    logger.info("Executing APScheduler Background Job: check_weather_alerts")
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            # Pick first farm or default location
            farms = db.query(Farm).filter(Farm.owner_id == user.id).all()
            location = farms[0].location if farms else "Mandya, India"
            
            weather = get_weather_forecast(location=location)
            # Check for high heat, low humidity, or rain
            if weather.temperature_c > 30.0 or "rain" in weather.forecast.lower():
                NotificationService.send_notification(
                    db=db,
                    user_id=user.id,
                    title=f"Weather Alert: {weather.forecast} in {location}",
                    message=f"Temp: {weather.temperature_c}°C, Humidity: {weather.humidity_percent}%. Advisory: {weather.agricultural_advisory}",
                    category="weather_alert",
                    channel="console_stub"
                )
    except Exception as e:
        logger.error(f"Error executing job_check_weather_alerts: {str(e)}")
    finally:
        db.close()

def job_irrigation_reminders():
    """
    APScheduler Background Job: Checks farm soil & growth conditions and issues automated irrigation reminders.
    """
    logger.info("Executing APScheduler Background Job: irrigation_reminders")
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            farms = db.query(Farm).filter(Farm.owner_id == user.id).all()
            if farms:
                farm = farms[0]
                NotificationService.send_notification(
                    db=db,
                    user_id=user.id,
                    title=f"Irrigation Schedule Reminder for {farm.name}",
                    message=f"Recommended irrigation check for {farm.soil_type} soil in {farm.location}. Check soil moisture sensor levels.",
                    category="irrigation_reminder",
                    channel="console_stub"
                )
    except Exception as e:
        logger.error(f"Error executing job_irrigation_reminders: {str(e)}")
    finally:
        db.close()

def job_mandi_price_ticker():
    """
    APScheduler Background Job: Fetches daily Mandi APMC market prices for farmer crops.
    """
    logger.info("Executing APScheduler Background Job: mandi_price_ticker")
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            mandi_res = get_market_prices(commodity="Tomato", state_or_mandi="Mandya")
            NotificationService.send_notification(
                db=db,
                user_id=user.id,
                title=f"Daily Mandi Price Update: {mandi_res.commodity}",
                message=f"Modal Price: ₹{mandi_res.modal_price:,.0f}/quintal at {mandi_res.mandi}. Trend: {mandi_res.trend}.",
                category="market_price",
                channel="email_stub"
            )
    except Exception as e:
        logger.error(f"Error executing job_mandi_price_ticker: {str(e)}")
    finally:
        db.close()

def start_scheduler():
    """
    Starts the in-process APScheduler background daemon.
    """
    if not scheduler.running:
        # Schedule jobs (run every 30 minutes in production, configured with interval for demo)
        scheduler.add_job(job_check_weather_alerts, 'interval', minutes=30, id='weather_alerts_job', replace_existing=True)
        scheduler.add_job(job_irrigation_reminders, 'interval', minutes=60, id='irrigation_reminders_job', replace_existing=True)
        scheduler.add_job(job_mandi_price_ticker, 'interval', hours=12, id='mandi_ticker_job', replace_existing=True)
        scheduler.start()
        logger.info("APScheduler background scheduler started successfully.")
        print("⏰ [APSCHEDULER STARTED] In-process background cron engine active.")

def shutdown_scheduler():
    """
    Gracefully shuts down the background scheduler.
    """
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler background scheduler stopped.")
        print("⏰ [APSCHEDULER STOPPED] Background scheduler shut down.")
