import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.config_loader import get_fetcher_config, get_contracts, get_ai_config, get_variety_for_code
from backend.fetcher.akshare_fetcher import (
    save_all_contracts_oi,
    fetch_and_save_all_members,
    fetch_and_save_variety_positions,
)
from backend.analyzer.llm_analyzer import generate_analysis, save_analysis

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def fetch_job():
    logger.info("定时: 采集合约OI")
    try:
        save_all_contracts_oi()
    except Exception as e:
        logger.error(f"合约OI失败: {e}")

    logger.info("定时: 采集机构持仓")
    try:
        fetch_and_save_all_members()
    except Exception as e:
        logger.error(f"机构持仓失败: {e}")

    logger.info("定时: 汇总品种排名")
    for c in get_contracts():
        try:
            fetch_and_save_variety_positions(c["code"])
        except Exception as e:
            logger.error(f"品种排名 {c['code']} 失败: {e}")


async def analyze_job():
    ai_config = get_ai_config()
    if not ai_config.get("api_key"):
        logger.warning("定时: AI分析跳过，未配置 API key")
        return

    for c in get_contracts():
        code = c["code"]
        variety = c.get("variety", code)
        try:
            content = await generate_analysis(symbol=code, variety=variety, days=30)
            save_analysis(code, content, period="1m")
            logger.info(f"定时: {code} 分析完成")
        except Exception as e:
            logger.error(f"定时: {code} 分析失败 - {e}")


def start_scheduler():
    fetcher_cfg = get_fetcher_config()
    schedule_time = fetcher_cfg.get("schedule_time", "16:30")
    try:
        hour, minute = schedule_time.split(":")
        hour, minute = int(hour), int(minute)
    except (ValueError, AttributeError):
        hour, minute = 16, 30

    scheduler.add_job(
        fetch_job,
        CronTrigger(hour=hour, minute=minute, day_of_week="mon-fri"),
        id="fetch_daily",
        replace_existing=True,
    )
    scheduler.add_job(
        analyze_job,
        CronTrigger(hour=hour, minute=minute + 10, day_of_week="mon-fri"),
        id="analyze_daily",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"定时调度已启动: 每日 {schedule_time}")


def stop_scheduler():
    scheduler.shutdown()
