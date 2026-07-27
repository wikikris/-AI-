import logging
from datetime import date, timedelta
from io import StringIO
from typing import Optional

import akshare as ak
import pandas as pd
import requests

from backend.config_loader import get_contracts, get_contract_codes, get_tracked_varieties

logger = logging.getLogger(__name__)


def _parse_int(value) -> int:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0
    try:
        return int(float(str(value).replace(",", "").replace(" ", "")))
    except (ValueError, TypeError):
        return 0


# ============ 合约日线 OI ============

def fetch_contract_daily(contract_code: str):
    try:
        df = ak.futures_zh_daily_sina(symbol=contract_code.upper())
        if df is not None and not df.empty:
            logger.info(f"获取 {contract_code} 日线: {len(df)} 条")
            return df
    except Exception as e:
        logger.error(f"获取 {contract_code} 日线失败: {e}")
    return pd.DataFrame()


def save_contract_oi(contract_code: str):
    from backend.models.database import SessionLocal, ContractOI

    df = fetch_contract_daily(contract_code)
    if df.empty:
        return {"status": "no_data", "code": contract_code, "saved": 0}

    col_set = set(df.columns)
    date_col = next((c for c in ["date", "日期"] if c in col_set), None)
    open_col = next((c for c in ["open", "开盘价"] if c in col_set), None)
    high_col = next((c for c in ["high", "最高价"] if c in col_set), None)
    low_col = next((c for c in ["low", "最低价"] if c in col_set), None)
    close_col = next((c for c in ["close", "收盘价"] if c in col_set), None)
    settle_col = next((c for c in ["settle", "结算价"] if c in col_set), None)
    vol_col = next((c for c in ["volume", "成交量"] if c in col_set), None)
    oi_col = next((c for c in ["hold", "持仓量"] if c in col_set), None)

    if not date_col:
        return {"status": "column_error", "code": contract_code}

    saved = 0
    db = SessionLocal()
    try:
        for _, row in df.iterrows():
            try:
                t_date = pd.to_datetime(row[date_col]).date()
            except Exception:
                continue

            existing = (
                db.query(ContractOI)
                .filter(ContractOI.trade_date == t_date, ContractOI.contract_code == contract_code)
                .first()
            )

            if existing is None:
                oi_val = _parse_int(row.get(oi_col)) if oi_col else 0

                prev_date = t_date - timedelta(days=1)
                prev_row = (
                    db.query(ContractOI)
                    .filter(
                        ContractOI.contract_code == contract_code,
                        ContractOI.trade_date == prev_date,
                    )
                    .first()
                )
                oi_change = oi_val - prev_row.open_interest if prev_row else 0

                item = ContractOI(
                    trade_date=t_date,
                    contract_code=contract_code,
                    open_price=float(row[open_col]) if open_col and pd.notna(row.get(open_col)) else 0,
                    high_price=float(row[high_col]) if high_col and pd.notna(row.get(high_col)) else 0,
                    low_price=float(row[low_col]) if low_col and pd.notna(row.get(low_col)) else 0,
                    close_price=float(row[close_col]) if close_col and pd.notna(row.get(close_col)) else 0,
                    settle_price=float(row[settle_col]) if settle_col and pd.notna(row.get(settle_col)) else 0,
                    volume=_parse_int(row.get(vol_col)) if vol_col else 0,
                    open_interest=oi_val,
                    oi_change=oi_change,
                )
                db.add(item)
                saved += 1

        db.commit()
        logger.info(f"保存 {contract_code} OI: {saved} 条")
    except Exception as e:
        db.rollback()
        logger.error(f"保存OI失败: {e}")
        raise
    finally:
        db.close()

    return {"status": "ok", "code": contract_code, "saved": saved}


def save_all_contracts_oi():
    results = []
    for code in get_contract_codes():
        r = save_contract_oi(code)
        results.append(r)
    return {"results": results}


# ============ 机构/会员持仓 (Sina API) ============

SINA_POS_URL = "https://vip.stock.finance.sina.com.cn/q/view/vFutures_Positions_cjcc.php"


def _fetch_sina_member_tables(contract_code: str, target_date: date) -> list:
    for offset in range(10):
        check_date = target_date - timedelta(days=offset)
        if check_date.weekday() >= 5:
            continue
        date_str = check_date.strftime("%Y-%m-%d")
        try:
            r = requests.get(SINA_POS_URL, params={"t_breed": contract_code.upper(), "t_date": date_str}, timeout=10)
            if r.status_code != 200 or len(r.text) < 2000:
                continue
            tables = pd.read_html(StringIO(r.text))
            if len(tables) >= 5:
                logger.info(f"获取 {contract_code} {date_str} 会员持仓: {len(tables)} 张表")
                return tables, check_date
        except Exception as e:
            logger.debug(f"尝试 {check_date} 失败: {e}")
            continue

    return [], target_date


def fetch_and_save_members(contract_code: str, target_date: Optional[date] = None) -> dict:
    from backend.models.database import SessionLocal, MemberPosition

    if target_date is None:
        target_date = date.today()

    tables, actual_date = _fetch_sina_member_tables(contract_code, target_date)

    if not tables or len(tables) < 4:
        return {"status": "no_data", "code": contract_code, "saved": 0}

    # Table mapping:
    # 0: nav, 1: header, 2: volume ranking, 3: long ranking, 4: short ranking
    vol_table = tables[2] if len(tables) > 2 else pd.DataFrame()
    long_table = tables[3] if len(tables) > 3 else pd.DataFrame()
    short_table = tables[4] if len(tables) > 4 else pd.DataFrame()

    # Build member data
    member_data = {}

    # Parse long table
    if not long_table.empty:
        for _, row in long_table.iterrows():
            name = str(row.iloc[1]) if len(row) > 1 else ""
            if not name or name == "nan" or name == "合计":
                continue
            long_pos = _parse_int(row.iloc[2]) if len(row) > 2 else 0
            long_chg = _parse_int(row.iloc[3]) if len(row) > 3 else 0
            member_data[name] = {"long": long_pos, "long_chg": long_chg, "short": 0, "short_chg": 0, "vol": 0}

    # Parse short table
    if not short_table.empty:
        for _, row in short_table.iterrows():
            name = str(row.iloc[1]) if len(row) > 1 else ""
            if not name or name == "nan" or name == "合计":
                continue
            short_pos = _parse_int(row.iloc[2]) if len(row) > 2 else 0
            short_chg = _parse_int(row.iloc[3]) if len(row) > 3 else 0
            if name in member_data:
                member_data[name]["short"] = short_pos
                member_data[name]["short_chg"] = short_chg
            else:
                member_data[name] = {"long": 0, "long_chg": 0, "short": short_pos, "short_chg": short_chg, "vol": 0}

    # Parse volume table
    if not vol_table.empty:
        for _, row in vol_table.iterrows():
            name = str(row.iloc[1]) if len(row) > 1 else ""
            if not name or name == "nan" or name == "合计":
                continue
            vol = _parse_int(row.iloc[2]) if len(row) > 2 else 0
            if name in member_data:
                member_data[name]["vol"] = vol
            else:
                member_data[name] = {"long": 0, "long_chg": 0, "short": 0, "short_chg": 0, "vol": vol}

    saved = 0
    db = SessionLocal()
    try:
        for member_name, data in member_data.items():
            # Skip members that only appear in volume table (both long and short are 0)
            if data["long"] == 0 and data["short"] == 0:
                continue

            existing = (
                db.query(MemberPosition)
                .filter(
                    MemberPosition.trade_date == actual_date,
                    MemberPosition.symbol == contract_code,
                    MemberPosition.member_name == member_name,
                )
                .first()
            )

            if existing is None:
                mp = MemberPosition(
                    trade_date=actual_date,
                    symbol=contract_code,
                    member_name=member_name,
                    long_position=data["long"],
                    long_change=data["long_chg"],
                    short_position=data["short"],
                    short_change=data["short_chg"],
                    net_position=data["long"] - data["short"],
                    net_change=data["long_chg"] - data["short_chg"],
                    volume=data["vol"],
                )
                db.add(mp)
                saved += 1

        db.commit()
        logger.info(f"保存 {contract_code} {actual_date} 会员持仓: {saved} 条")
    except Exception as e:
        db.rollback()
        logger.error(f"保存会员持仓失败: {e}")
        raise
    finally:
        db.close()

    return {"status": "ok", "code": contract_code, "date": str(actual_date), "saved": saved}


def fetch_and_save_members_multi(contract_code: str, num_days: int = 7, end_date: Optional[date] = None) -> dict:
    if end_date is None:
        end_date = date.today()

    total_saved = 0
    results = []
    days_collected = 0

    for offset in range(num_days * 2):
        check_date = end_date - timedelta(days=offset)
        if check_date.weekday() >= 5:
            continue
        r = fetch_and_save_members(contract_code, check_date)
        if r.get("saved", 0) > 0:
            results.append(r)
            total_saved += r["saved"]
            days_collected += 1
            if days_collected >= num_days:
                break

    return {"status": "ok", "code": contract_code, "days_collected": days_collected, "total_saved": total_saved, "details": results}


def fetch_and_save_all_members(target_date: Optional[date] = None, num_days: int = 1) -> dict:
    results = []
    total = 0
    for c in get_contracts():
        code = c["code"]
        r = fetch_and_save_members_multi(code, num_days=num_days, end_date=target_date)
        results.append(r)
        total += r.get("total_saved", 0)
    return {"status": "ok", "total_saved": total, "details": results}


# ============ 品种持仓排名 (使用合约级OI汇总) ============

def fetch_and_save_variety_positions(contract_code: str):
    from backend.models.database import SessionLocal, DailyPosition, MemberPosition
    from backend.config_loader import get_variety_for_code
    variety = get_variety_for_code(contract_code)

    db = SessionLocal()
    try:
        # Get all unique dates with member data
        dates = (
            db.query(MemberPosition.trade_date)
            .filter(MemberPosition.symbol == contract_code)
            .distinct()
            .order_by(MemberPosition.trade_date.asc())
            .all()
        )

        saved = 0
        for (t_date,) in dates:
            members = (
                db.query(MemberPosition)
                .filter(
                    MemberPosition.symbol == contract_code,
                    MemberPosition.trade_date == t_date,
                )
                .all()
            )
            if not members:
                continue

            # Filter: only members with actual long OR short positions
            active_members = [m for m in members if m.long_position > 0 or m.short_position > 0]
            if not active_members:
                continue

            top5_long = sum(sorted([m.long_position for m in active_members], reverse=True)[:5])
            top5_short = sum(sorted([m.short_position for m in active_members], reverse=True)[:5])
            top10_long = sum(sorted([m.long_position for m in active_members], reverse=True)[:10])
            top10_short = sum(sorted([m.short_position for m in active_members], reverse=True)[:10])
            total_long = sum(m.long_position for m in active_members)
            total_short = sum(m.short_position for m in active_members)

            existing = (
                db.query(DailyPosition)
                .filter(
                    DailyPosition.trade_date == t_date,
                    DailyPosition.symbol == contract_code,
                )
                .first()
            )

            if existing is None:
                pos = DailyPosition(
                    trade_date=t_date,
                    symbol=contract_code,
                    exchange="",
                    variety_name=variety,
                    long_position=total_long,
                    short_position=total_short,
                    net_position=total_long - total_short,
                    top5_long=top5_long,
                    top5_short=top5_short,
                    top10_long=top10_long,
                    top10_short=top10_short,
                )
                db.add(pos)
                saved += 1

        db.commit()
        logger.info(f"品种排名 {contract_code}: 聚合了 {saved} 天数据")
    except Exception as e:
        db.rollback()
        logger.error(f"品种排名聚合失败: {e}")
    finally:
        db.close()


def fetch_all(target_date: Optional[date] = None) -> dict:
    contracts_result = save_all_contracts_oi()

    # Fetch 7 days of member data for trend charts
    members_result = fetch_and_save_all_members(target_date, num_days=7)

    # Aggregate DailyPosition for all dates
    for c in get_contracts():
        fetch_and_save_variety_positions(c["code"])

    return {
        "contracts": contracts_result,
        "members": members_result,
    }
