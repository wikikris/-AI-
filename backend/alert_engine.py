"""预警引擎：换月提醒、集中度预警、席位命中率、自定义预警"""


def check_all(contract_code: str) -> list:
    from backend.models.database import SessionLocal, ContractOI, MemberPosition
    db = SessionLocal()
    alerts = []
    try:
        alerts += _check_roll(contract_code, db)
        alerts += _check_concentration(contract_code, db)
    finally:
        db.close()
    return alerts


def _check_roll(contract_code: str, db) -> list:
    from backend.models.database import ContractOI
    rows = (
        db.query(ContractOI)
        .filter(ContractOI.contract_code == contract_code.upper())
        .order_by(ContractOI.trade_date.desc())
        .limit(10)
        .all()
    )
    if len(rows) < 5:
        return []

    recent = rows[:5]
    oi_values = [r.open_interest for r in recent if r.open_interest]

    if len(oi_values) >= 5:
        first = oi_values[0]
        last = oi_values[-1]
        if first > 0 and last > 0:
            pct = (first - last) / last * 100
            decreasing = all(oi_values[i] < oi_values[i + 1] for i in range(len(oi_values) - 1))
            if decreasing and pct > 15:
                return [{"type": "roll", "level": "warn",
                         "msg": f"{contract_code} 持仓 5 日连降 {pct:.1f}%，可能正在换月，注意切换合约"}]

    return []


def _check_concentration(contract_code: str, db) -> list:
    from backend.models.database import MemberPosition
    from sqlalchemy import func
    latest = (
        db.query(func.max(MemberPosition.trade_date))
        .filter(MemberPosition.symbol == contract_code.upper())
        .scalar()
    )
    if not latest:
        return []

    members = (
        db.query(MemberPosition)
        .filter(MemberPosition.symbol == contract_code.upper(), MemberPosition.trade_date == latest)
        .all()
    )
    if not members:
        return []

    total_long = sum(m.long_position for m in members)
    total_short = sum(m.short_position for m in members)
    top3_long = sum(sorted([m.long_position for m in members], reverse=True)[:3])
    top3_short = sum(sorted([m.short_position for m in members], reverse=True)[:3])

    alerts = []
    if total_long > 0 and top3_long / total_long > 0.6:
        alerts.append({"type": "concentration", "level": "warn",
                       "msg": f"{contract_code} 多头集中度 {top3_long/total_long*100:.0f}%，Top3 高度控盘"})
    if total_short > 0 and top3_short / total_short > 0.6:
        alerts.append({"type": "concentration", "level": "warn",
                       "msg": f"{contract_code} 空头集中度 {top3_short/total_short*100:.0f}%，Top3 高度控盘"})
    return alerts


def get_seat_accuracy(symbol: str) -> list:
    """席位近期命中率：统计各机构过去 N 天的净持仓方向 vs 收盘涨跌"""
    from backend.models.database import SessionLocal, ContractOI, MemberPosition
    db = SessionLocal()
    try:
        # Get OI data for price direction
        oi_rows = (
            db.query(ContractOI)
            .filter(ContractOI.contract_code == symbol.upper())
            .order_by(ContractOI.trade_date.desc())
            .limit(30)
            .all()
        )
        if not oi_rows:
            return []

        member_rows = (
            db.query(MemberPosition)
            .filter(MemberPosition.symbol == symbol.upper())
            .order_by(MemberPosition.trade_date.desc())
            .limit(500)
            .all()
        )

        date_price = {}
        for i in range(1, len(oi_rows)):
            date_price[str(oi_rows[i].trade_date)] = oi_rows[i - 1].close_price - oi_rows[i].close_price

        member_scores = {}
        member_counts = {}
        for m in member_rows:
            dt = str(m.trade_date)
            if dt not in date_price:
                continue
            name = m.member_name
            if name not in member_scores:
                member_scores[name] = 0
                member_counts[name] = 0
            member_counts[name] += 1
            price_up = date_price[dt] > 0
            if (m.net_position > 0 and price_up) or (m.net_position < 0 and not price_up):
                member_scores[name] += 1

        result = []
        for name in member_scores:
            cnt = member_counts[name]
            if cnt >= 3:
                acc = round(member_scores[name] / cnt * 100)
                tag = ""
                if acc >= 70:
                    tag = "正指"
                elif acc <= 40:
                    tag = "反指"
                result.append({"name": name, "accuracy": acc, "samples": cnt, "tag": tag})

        result.sort(key=lambda x: -x["accuracy"])
        return result[:20]
    finally:
        db.close()


def get_brief(contract_codes: list, indicators_data: dict) -> str:
    """生成今日异动简报文本"""
    lines = []
    for code in contract_codes:
        ind = indicators_data.get(code, {})
        if not ind:
            if code in indicators_data:
                lines.append(f"{code}: 暂无数据")
            continue

        tech = ind.get("tech", {})
        price_chg = tech.get("price_vs_MA5", 0)
        oi_5d = tech.get("oi_5d_change", 0)
        ma = tech.get("ma_alignment", "?")
        vol_ratio = tech.get("volume_ratio", 1)

        parts = [code]
        if abs(price_chg) >= 0.5:
            parts.append(f"{'涨' if price_chg>0 else '跌'}{abs(price_chg):.1f}%")
        if abs(oi_5d) >= 1000:
            sign = "增" if oi_5d>0 else "减"
            val = abs(oi_5d)
            s = f"{val}" if val<10000 else f"{val/10000:.1f}万"
            parts.append(f"OI{sign}{s}")

        if len(parts) > 1:
            lines.append(" · ".join(parts))

    if not lines:
        return "今日无异常数据"
    return " | ".join(lines)
