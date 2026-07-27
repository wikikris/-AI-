import logging
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.config_loader import load_config, get_contracts, get_contract_codes, get_variety_for_code, save_config, reload_config
from backend.models.database import get_db, DailyPosition, MemberPosition, ContractOI, AnalysisReport
from backend.fetcher.akshare_fetcher import (
    save_all_contracts_oi,
    save_contract_oi,
    fetch_and_save_members,
    fetch_and_save_all_members,
    fetch_and_save_variety_positions,
    fetch_all,
)
from backend.analyzer.llm_analyzer import (
    generate_analysis, save_analysis, get_latest_analysis, get_analysis_history, chat_followup,
)
from backend.alert_engine import check_all, get_seat_accuracy, get_brief

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


class ContractRequest(BaseModel):
    code: str
    variety: Optional[str] = None
    exchange: Optional[str] = None


class FetchRequest(BaseModel):
    target_date: Optional[str] = None
    include_members: bool = True


class AnalyzeRequest(BaseModel):
    contract_code: str
    period: Optional[str] = "1m"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    days: Optional[int] = None


def _parse_period(period: str, days: int) -> tuple:
    today = date.today()
    mapping = {"1w": 7, "2w": 14, "1m": 30, "3m": 90, "6m": 180, "1y": 365}
    d = mapping.get(period, max(1, min(days or 30, 365)))
    return today - timedelta(days=d), today, d


# ============ 合约管理 ============

@router.get("/contracts")
def list_contracts():
    return {"contracts": get_contracts()}


@router.post("/contracts")
def add_contract(req: ContractRequest):
    config = load_config()
    contracts = config.setdefault("contracts", [])
    for c in contracts:
        if c["code"].upper() == req.code.upper():
            raise HTTPException(400, f"合约 {req.code} 已存在")
    contracts.append({"code": req.code.upper(), "variety": req.variety or "", "exchange": req.exchange or ""})
    save_config(config)
    reload_config()
    return {"status": "ok", "message": f"已添加合约 {req.code}"}


@router.delete("/contracts/{code}")
def remove_contract(code: str):
    config = load_config()
    contracts = config.setdefault("contracts", [])
    for i, c in enumerate(contracts):
        if c["code"].upper() == code.upper():
            contracts.pop(i)
            save_config(config)
            reload_config()
            return {"status": "ok", "message": f"已移除合约 {code}"}
    raise HTTPException(404, f"未找到合约 {code}")


# ============ 合约日线 OI ============

@router.get("/contracts/{code}/oi")
def get_contract_oi(
    code: str,
    period: str = Query(default="3m"),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    if start_date and end_date:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    else:
        start, end, _ = _parse_period(period, 90)

    rows = (
        db.query(ContractOI)
        .filter(ContractOI.contract_code == code.upper(), ContractOI.trade_date >= start, ContractOI.trade_date <= end)
        .order_by(ContractOI.trade_date.asc())
        .all()
    )

    return {
        "contract_code": code.upper(),
        "count": len(rows),
        "data": [
            {
                "date": str(r.trade_date),
                "open": r.open_price, "high": r.high_price, "low": r.low_price,
                "close": r.close_price, "settle": r.settle_price,
                "volume": r.volume, "open_interest": r.open_interest, "oi_change": r.oi_change,
            }
            for r in rows
        ],
    }


# ============ 品种排名 (从会员汇总) ============

@router.get("/positions/{code}")
def get_positions(
    code: str,
    period: str = Query(default="1m"),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    if start_date and end_date:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    else:
        start, end, _ = _parse_period(period, 30)

    rows = (
        db.query(DailyPosition)
        .filter(DailyPosition.symbol == code.upper(), DailyPosition.trade_date >= start, DailyPosition.trade_date <= end)
        .order_by(DailyPosition.trade_date.asc())
        .all()
    )

    return {
        "contract_code": code,
        "variety": get_variety_for_code(code),
        "count": len(rows),
        "data": [
            {
                "date": str(r.trade_date),
                "long_position": r.long_position, "short_position": r.short_position,
                "net_position": r.net_position,
                "top5_long": r.top5_long, "top5_short": r.top5_short,
                "top10_long": r.top10_long, "top10_short": r.top10_short,
            }
            for r in rows
        ],
    }


# ============ 机构持仓 ============

@router.get("/positions/{code}/members")
def get_member_positions(
    code: str,
    period: str = Query(default="1m"),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    if start_date and end_date:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    else:
        start, end, _ = _parse_period(period, 30)

    latest_date_row = (
        db.query(func.max(MemberPosition.trade_date))
        .filter(MemberPosition.symbol == code.upper(), MemberPosition.trade_date <= end)
        .scalar()
    )

    if not latest_date_row:
        return {"contract_code": code, "members": [], "note": "暂无机构持仓数据"}

    start_date_row = (
        db.query(func.max(MemberPosition.trade_date))
        .filter(MemberPosition.symbol == code.upper(), MemberPosition.trade_date >= start)
        .scalar()
    )

    latest = (
        db.query(MemberPosition)
        .filter(MemberPosition.symbol == code.upper(), MemberPosition.trade_date == latest_date_row)
        .order_by(MemberPosition.net_position.desc())
        .all()
    )

    members = []
    for m in latest:
        if m.long_position == 0 and m.short_position == 0:
            continue

        prev_m = None
        if start_date_row:
            prev_m = (
                db.query(MemberPosition)
                .filter(
                    MemberPosition.symbol == code.upper(),
                    MemberPosition.trade_date == start_date_row,
                    MemberPosition.member_name == m.member_name,
                )
                .first()
            )

        period_long_chg = m.long_position - prev_m.long_position if prev_m else 0
        period_short_chg = m.short_position - prev_m.short_position if prev_m else 0

        members.append({
            "member_name": m.member_name,
            "long_position": m.long_position, "long_change": m.long_change,
            "short_position": m.short_position, "short_change": m.short_change,
            "net_position": m.net_position, "net_change": m.net_change,
            "period_long_chg": period_long_chg, "period_short_chg": period_short_chg,
            "period_net_chg": period_long_chg - period_short_chg,
        })

    return {
        "contract_code": code,
        "date": str(latest_date_row),
        "member_count": len(members),
        "members": members,
    }


@router.get("/positions/{code}/member-trend")
def get_member_trend(
    code: str,
    member_names: str = Query(default=""),
    period: str = Query(default="1m"),
    db: Session = Depends(get_db),
):
    names = [n.strip() for n in member_names.split(",") if n.strip()] if member_names else []
    start, end, _ = _parse_period(period, 30)

    if not names:
        subq = (
            db.query(MemberPosition.member_name, func.sum(func.abs(MemberPosition.net_position)).label("total"))
            .filter(MemberPosition.symbol == code.upper(), MemberPosition.trade_date >= start, MemberPosition.trade_date <= end)
            .group_by(MemberPosition.member_name)
            .order_by(func.sum(func.abs(MemberPosition.net_position)).desc())
            .limit(10)
            .subquery()
        )
        name_rows = db.query(subq.c.member_name).all()
        names = [r[0] for r in name_rows]

    result = {}
    for name in names:
        rows = (
            db.query(MemberPosition)
            .filter(
                MemberPosition.symbol == code.upper(),
                MemberPosition.member_name == name,
                MemberPosition.trade_date >= start,
                MemberPosition.trade_date <= end,
            )
            .order_by(MemberPosition.trade_date.asc())
            .all()
        )
        result[name] = [
            {"date": str(r.trade_date), "net": r.net_position, "long": r.long_position, "short": r.short_position}
            for r in rows
        ]

    return {"contract_code": code, "members": result}


# ============ 仪表盘 ============

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    contracts = get_contracts()
    items = []
    for c in contracts:
        code = c["code"]
        variety = c.get("variety", code)

        oi_latest = (
            db.query(ContractOI)
            .filter(ContractOI.contract_code == code)
            .order_by(ContractOI.trade_date.desc())
            .first()
        )

        pos_latest = (
            db.query(DailyPosition)
            .filter(DailyPosition.symbol == code)
            .order_by(DailyPosition.trade_date.desc())
            .first()
        )

        analysis = get_latest_analysis(code)

        items.append({
            "contract_code": code,
            "variety": variety,
            "contract_oi": {
                "date": str(oi_latest.trade_date) if oi_latest else None,
                "close": oi_latest.close_price if oi_latest else 0,
                "open_interest": oi_latest.open_interest if oi_latest else 0,
                "oi_change": oi_latest.oi_change if oi_latest else 0,
                "volume": oi_latest.volume if oi_latest else 0,
            },
            "variety_position": {
                "date": str(pos_latest.trade_date) if pos_latest else None,
                "net_position": pos_latest.net_position if pos_latest else 0,
                "long_position": pos_latest.long_position if pos_latest else 0,
                "short_position": pos_latest.short_position if pos_latest else 0,
            },
            "analysis_summary": analysis["content"][:300] if analysis and analysis.get("content") else None,
            "analysis_period": analysis.get("period") if analysis else None,
        })

    return {"data": items}


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    contracts = get_contracts()
    items = []
    for c in contracts:
        code = c["code"]
        oi_latest = (
            db.query(ContractOI)
            .filter(ContractOI.contract_code == code)
            .order_by(ContractOI.trade_date.desc())
            .first()
        )

        oi_rows = (
            db.query(ContractOI)
            .filter(ContractOI.contract_code == code)
            .order_by(ContractOI.trade_date.desc())
            .limit(5)
            .all()
        )
        oi_5d_chg = 0
        if len(oi_rows) >= 2:
            oi_5d_chg = oi_rows[0].open_interest - oi_rows[-1].open_interest

        oi_change_pct = 0
        if oi_latest and oi_latest.open_interest and oi_latest.oi_change:
            oi_change_pct = round(oi_latest.oi_change / oi_latest.open_interest * 100, 2)

        items.append({
            "contract_code": code,
            "variety": get_variety_for_code(code),
            "latest_date": str(oi_latest.trade_date) if oi_latest else None,
            "close": oi_latest.close_price if oi_latest else 0,
            "open_interest": oi_latest.open_interest if oi_latest else 0,
            "oi_change_daily": oi_latest.oi_change if oi_latest else 0,
            "oi_change_pct": oi_change_pct,
            "oi_change_5d": oi_5d_chg,
            "volume": oi_latest.volume if oi_latest else 0,
        })

    return {"data": items}


# ============ 数据采集 ============

@router.post("/fetch")
def trigger_fetch(req: FetchRequest = None):
    target = None
    if req and req.target_date:
        try:
            target = datetime.strptime(req.target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(400, "日期格式错误 YYYY-MM-DD")

    result = fetch_all(target_date=target)
    return result


@router.post("/fetch/{code}")
def trigger_fetch_one(code: str, req: FetchRequest = None):
    target = None
    if req and req.target_date:
        try:
            target = datetime.strptime(req.target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(400, "日期格式错误")

    return {
        "contract_oi": save_contract_oi(code),
        "member_positions": fetch_and_save_members(code, target_date=target),
    }


@router.get("/fetch/latest-date")
def get_latest_fetch_date(db: Session = Depends(get_db)):
    oi_row = db.query(ContractOI).order_by(ContractOI.trade_date.desc()).first()
    memb_row = db.query(MemberPosition).order_by(MemberPosition.trade_date.desc()).first()
    return {
        "latest_contract_date": str(oi_row.trade_date) if oi_row else None,
        "latest_member_date": str(memb_row.trade_date) if memb_row else None,
    }


# ============ AI 分析 ============

@router.post("/analysis/generate")
async def trigger_analysis(req: AnalyzeRequest):
    code = req.contract_code
    days = req.days
    if req.period and not req.start_date:
        period_map = {"1w": 7, "2w": 14, "1m": 30, "3m": 90, "6m": 180, "1y": 365}
        days = period_map.get(req.period, days or 30)

    variety = get_variety_for_code(code)
    content = await generate_analysis(
        symbol=code,
        variety=variety,
        days=days,
        start_date=req.start_date,
        end_date=req.end_date,
    )

    period_label = req.period or "1m"
    save_analysis(code, content, period=period_label)
    return {"contract_code": code, "variety": variety, "period": period_label, "content": content}


@router.get("/analysis/{code}")
def get_analysis(code: str):
    result = get_latest_analysis(code)
    if result:
        return result
    return {"contract_code": code, "content": "暂无分析报告"}


@router.get("/analysis/{code}/history")
def get_analysis_hist(code: str, limit: int = 20):
    return {"contract_code": code, "history": get_analysis_history(code, limit)}


@router.get("/export/{code}")
def export_data(code: str, db: Session = Depends(get_db)):
    """导出CSV: 合约OI + 机构持仓"""
    import csv, io
    output = io.StringIO()
    w = csv.writer(output)

    # OI header
    oi_rows = db.query(ContractOI).filter(ContractOI.contract_code == code.upper()).order_by(ContractOI.trade_date.asc()).all()
    w.writerow(["=== 合约日线数据 ==="])
    w.writerow(["日期","开盘","最高","最低","收盘","结算","成交量","持仓量","OI变化"])
    for r in oi_rows:
        w.writerow([str(r.trade_date),r.open_price,r.high_price,r.low_price,r.close_price,r.settle_price,r.volume,r.open_interest,r.oi_change])

    # Member header
    w.writerow([])
    w.writerow(["=== 机构持仓数据 ==="])
    members = db.query(MemberPosition).filter(MemberPosition.symbol == code.upper()).order_by(MemberPosition.trade_date.desc(),MemberPosition.net_position.desc()).all()
    w.writerow(["日期","机构名称","多头持仓","多头日变","空头持仓","空头日变","净持仓","净日变","成交量"])
    for m in members:
        w.writerow([str(m.trade_date),m.member_name,m.long_position,m.long_change,m.short_position,m.short_change,m.net_position,m.net_change,m.volume])

    from fastapi.responses import StreamingResponse
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]),media_type="text/csv",headers={"Content-Disposition":f"attachment;filename={code}_export.csv"})


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    contract_code: str
    question: str
    analysis_context: str = ""
    history: list = []


@router.post("/analysis/chat")
async def chat(req: ChatRequest):
    reply = await chat_followup(
        contract_code=req.contract_code,
        question=req.question,
        analysis_context=req.analysis_context,
        history=req.history,
    )
    return {"reply": reply}


# ============ 配置管理 ============

class ConfigAI(BaseModel):
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 3000


class ConfigFetcher(BaseModel):
    schedule_time: str = "16:30"
    retry: int = 3


class ConfigUpdate(BaseModel):
    contracts: Optional[list] = None
    ai: Optional[ConfigAI] = None
    fetcher: Optional[ConfigFetcher] = None


class ContractItem(BaseModel):
    code: str
    variety: str = ""
    exchange: str = ""


class ContractsUpdate(BaseModel):
    contracts: list


@router.get("/config")
def get_config():
    config = load_config()
    ai = dict(config.get("ai", {}))
    if ai.get("api_key") and len(ai["api_key"]) > 8:
        ai["api_key"] = ai["api_key"][:4] + "****" + ai["api_key"][-4:]
    return {
        "contracts": config.get("contracts", []),
        "ai": ai,
        "fetcher": config.get("fetcher", {}),
    }


@router.put("/config")
def update_config(req: ConfigUpdate):
    config = load_config()
    if req.contracts is not None:
        config["contracts"] = req.contracts
    if req.ai is not None:
        config["ai"] = req.ai.model_dump()
    if req.fetcher is not None:
        config["fetcher"] = req.fetcher.model_dump()
    save_config(config)
    reload_config()
    return {"status": "ok"}


@router.put("/config/contracts")
def update_contracts(req: ContractsUpdate):
    config = load_config()
    config["contracts"] = req.contracts
    save_config(config)
    reload_config()
    return {"status": "ok", "count": len(req.contracts)}


@router.put("/config/ai")
def update_ai(req: ConfigAI):
    config = load_config()
    config["ai"] = req.model_dump()
    save_config(config)
    reload_config()
    return {"status": "ok"}


# ============ 预警 + 简报 + 命中率 ============

@router.get("/alerts/{code}")
def get_alerts(code: str):
    return {"code": code, "alerts": check_all(code)}


@router.get("/alerts")
def get_all_alerts(db: Session = Depends(get_db)):
    contracts = get_contracts()
    all_alerts = []
    for c in contracts:
        for a in check_all(c["code"]):
            all_alerts.append({"contract": c["code"], **a})

    # Brief
    from backend.analyzer.llm_analyzer import _compute_indicators
    indicators = {}
    for c in contracts:
        today = date.today()
        indicators[c["code"]] = _compute_indicators(c["code"], today - timedelta(days=7), today)
    brief = get_brief([c["code"] for c in contracts], indicators)

    return {"alerts": all_alerts, "brief": brief}


@router.get("/seats/{code}/accuracy")
def seat_accuracy(code: str):
    return {"code": code, "seats": get_seat_accuracy(code)}
