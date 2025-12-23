from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.services.stats import collect_daily_stats

# Создаем планировщик
scheduler = AsyncIOScheduler()

def start_scheduler():
    """
    Запускает планировщик задач.
    """
    # Добавляем задачу на выполнение каждый день в 23:55
    scheduler.add_job(collect_daily_stats, 'cron', hour=23, minute=55)
    
    scheduler.start()