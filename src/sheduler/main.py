import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

scheduler = AsyncIOScheduler()

async def remind():
    print(f"[{datetime.now()}] ⏰ Напоминание!")

async def main():
    scheduler.start()
    scheduler.add_job(remind, "interval", minutes=30)
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
