import sys
import os
import time
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Ensure root is in path
sys.path.append(os.getcwd())

from services.worker.tasks import train_job_all_coins

# Setup Logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("WorkerMain")

def main():
    logger.info("Initializing Worker Service...")
    
    scheduler = BlockingScheduler()
    
    # Schedule Job: Daily at 00:00 UTC
    trigger = CronTrigger(hour=0, minute=0, timezone='UTC')
    scheduler.add_job(train_job_all_coins, trigger, id='daily_training')
    
    logger.info("Scheduler started. Next run at: " + str(trigger))
    
    # OPTIONAL: Run once immediately on startup?
    # Usually good for verification/demos, but might be heavy in prod if restarts are frequent.
    # For this project, let's run it if env var RUN_ON_STARTUP is set.
    if os.getenv("RUN_ON_STARTUP", "True").lower() == "true":
         logger.info("Creating initial model versions (RUN_ON_STARTUP=True)...")
         # We run it in a separate thread or just block? Blocking is safer for init.
         try:
             train_job_all_coins()
         except Exception as e:
             logger.error(f"Initial run failed: {e}")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    main()
