import logging
import re
from datetime import date, timedelta

import httpx

from backend.config_loader import get_ai_config
from backend.models.database import SessionLocal, MemberPosition, ContractOI, AnalysisReport

logger = logging.getLogger(__name__)

# ============================================================
# 机构画像
# ============================================================
INSTITUTION_PROFILES = {
    "永安期货": {"style": "产业套保+基本面投机", "strength": "黑色系、农产品",
                  "indicator": "正指-对黑色/农产品有领先性", "signal": "增多=看多; 增空=产业套保压力"},
    "中信期货": {"style": "综合券商系", "strength": "全品种",
                  "indicator": "正指-市场容量最大,代表主流资金态度", "signal": "单边大幅增减仓=市场共识"},
    "国泰君安": {"style": "大型综合稳健", "strength": "金融期货、有色金属",
                  "indicator": "偏正指-机构化运作,方向可靠", "signal": "持续增仓=中长期趋势确认"},
    "混沌天成": {"style": "投机驱动", "strength": "全品种",
                  "indicator": "反指-极端单边重仓常出现在趋势末端", "signal": "极值仓位=警惕反转"},
    "方正中期": {"style": "技术分析派", "strength": "黑色系、化工",
                  "indicator": "偏正指-趋势判断敏锐,切换快", "signal": "快速多空切换=趋势可能转折"},
    "申万期货": {"style": "研究驱动", "strength": "全品种",
                  "indicator": "正指-基本面+宏观结合", "signal": "持续增仓方向=基本面支撑"},
    "中粮期货": {"style": "产业套保", "strength": "农产品(豆粕/油脂)",
                  "indicator": "农产品正指-现货信息优势", "signal": "增多=下游需求; 增空=供应宽松"},
    "中信建投": {"style": "券商系趋势", "strength": "全品种",
                  "indicator": "偏正指-规模第二大券商系", "signal": "与中信同向=强确认"},
    "海通期货": {"style": "综合国际化", "strength": "有色金属、能源",
                  "indicator": "中性-外盘联动影响大", "signal": "需结合外盘判断"},
    "东证期货": {"style": "量化/程序化", "strength": "全品种",
                  "indicator": "偏正指-模型驱动", "signal": "异常增仓=趋势可能加速"},
    "华泰期货": {"style": "量化+短线", "strength": "金融期货、黑色系",
                  "indicator": "偏反指-方向持续性弱", "signal": "单日大幅=可能一日游"},
    "银河期货": {"style": "综合套保", "strength": "全品种",
                  "indicator": "中性偏正指-产业客户多", "signal": "突然大幅增减=产业集中入场"},
    "南华期货": {"style": "国际化布局", "strength": "有色金属、能源",
                  "indicator": "偏正指-外盘研究能力强", "signal": "跨境套利信号有价值"},
    "浙商期货": {"style": "江浙资本", "strength": "化工(PTA/甲醇)",
                  "indicator": "化工板块风向标", "signal": "化工品集中增减=产业链信号"},
    "一德期货": {"style": "北方产业系", "strength": "黑色系",
                  "indicator": "黑色系正指-产业基础好", "signal": "大幅动作=关注钢厂基本面"},
}

# ============================================================
# 系统提示词 (均线+多周期+技术分析)
# ============================================================
SYSTEM_PROMPT = """你是一位期货持仓分析师。基于量价数据、机构持仓、技术指标输出分析报告。

## 格式规则

- **严禁**任何开场白、客套话、称呼，直接输出报告正文
- **严禁**使用 Markdown 表格、加粗、分割线等排版装饰
- 用纯文本分段，每段标题用【】括起来
- 引用数据时必须带具体数字和机构名称
- 整篇报告控制在 1200 字以内
- 结论必须从数据归纳得出，不能先定方向再找证据

## 输入数据的含义说明

你收到的数据中：
- 多头/空头 = 各机构在该合约上的持买单量/持卖单量（不是成交量）
- 日变 = 相比上一交易日的变化（+ 加仓、- 减仓）
- 净持仓 = 多头 - 空头
- 多空比 = 所有机构多头总量 ÷ 空头总量

## 分析框架

核心思路：每一步分析都要回答"谁在做什么，为什么，意味着什么"。

【持仓驱动力拆解】 ← 第1段

不要先下结论。先拆数据，再归纳。

1. 本期整体发生了什么：价格涨跌多少？OI增还是减？多空比变化？
2. 拆解驱动力：
   - 多头侧：谁在加多？谁在减多？多头总量净变化多少？
   - 空头侧：谁在加空？谁在减空？空头总量净变化多少？
   - 哪一方的动作主导了价格变化？（比较多头净变化 vs 空头净变化的绝对值）
3. 归纳：这轮价格变动主要是谁在推动？用的什么方式（增仓进攻/减仓撤退）？
4. 给出现状画像：经过本期变化后，多空双方各处于什么状态？

注意：参考20日趋势作为背景，但不预设结论。20日涨了6%而本周跌了1%，可能只是回调，也可能真的是多头在撤退——具体要看数据里谁在减仓、减了多少。

示例（这才叫从数据出发）：
"本周多头总量减x万手，其中A席位减y万手、B席位减z万手，合计占多头总减量的70%。空头总量基本不变。价格跌1.2%主要由多头主动平仓驱动。结合20日背景看，20日内多头曾增仓a万手推动价格涨6%，本周部分多头选择在反弹高位止盈。这是获利了结而非趋势逆转——除非接下来多头继续大幅减仓。"
2. 如果是减仓驱动的价格变化，谁在减？减了多少？为什么减（止盈/止损/换月）？
3. 增量资金的方向：新开仓的钱去了多头还是空头？新增的头寸代表了什么预期？
4. 多空双方的博弈状态：是一方压倒性优势，还是势均力敌？OI在扩张还是收缩？
5. 绝对水平：当前OI在近期历史中处于什么位置？天量OI意味着分歧极大，低OI意味着方向已明或无人关注

示例分析逻辑链：
"价格涨了6%但OI降了43万手 → 不是多头主动进攻，是空头大规模平仓 → 看数据发现国泰君安净空单日减1.2万手、中信净空减0.4万手 → 正指空头主力撤退 → 反弹由空头踩踏离场驱动 → 可持性取决于空头是否继续离场、多头是否跟进"

每个结论必须引用具体机构名称和数字。

【席位深度追踪】 ← 第2段

不是罗列席位，而是追踪"谁在动"：
- 本期净持仓变化最大的5个席位具体做了什么？多增还是空减？
- 有没有席位出现方向性转向（多翻空/空翻多）？转向幅度多大？
- 如果多个席位同时向同一方向转向，这是集体行为信号，权重极高
- 席位行为的"组团"特征：中信系（中信期货+中信建投）是否一致？产业系（永安+一德）是否同向？
- 正指反指作为参考注记即可，不须单独成段：在提到某席位时用括号标注"(正指)"或"(反指)"即可

【多周期验证】 ← 第3段

以20日趋势为锚点，判断本期行为：
- 20日趋势方向是什么？本期是顺应还是回调？
- 回调是否破坏20日趋势？看持仓变化：OI在顺势还是逆势？
- 如果20日多头 + 本期减仓下跌 = 多头趋势中的调整，关注多头是否仍在还是大规模离场
- 对比本期OI变化速度 vs 20日平均变化速度，判断是否加速/减速

【技术面参考】 ← 第4段，不超过5行

仅用均线排列和关键位做确认，不展开分析。持仓结论为主。

【综合研判】

- 核心叙事：用2-3句话总结当前持仓格局的核心矛盾
- 驱动力归因：价格变化X%来自什么持仓行为（量化归因）
- 可持性判断：当前格局能持续吗？什么情况下会被打破？
- 关键观察点：接下来盯哪个席位、哪个数据？
"""


# ============================================================
# 数据工具函数
# ============================================================

def _ma(values: list, n: int) -> float:
    if len(values) < n:
        return values[-1] if values else 0
    return sum(values[-n:]) / n


def _high(values: list, n: int) -> float:
    return max(values[-n:]) if len(values) >= n else (max(values) if values else 0)


def _low(values: list, n: int) -> float:
    return min(values[-n:]) if len(values) >= n else (min(values) if values else 0)


# ============================================================
# 技术指标计算
# ============================================================

def _compute_technical_indicators(contract_code: str, db) -> dict:
    """计算均线、支撑压力、趋势阶段等全部技术指标"""
    tech = {}

    # 获取足够长的历史数据(至少60天用于MA60)
    rows = (
        db.query(ContractOI)
        .filter(ContractOI.contract_code == contract_code.upper())
        .order_by(ContractOI.trade_date.asc())
        .all()
    )

    if len(rows) < 10:
        return tech

    closes = [r.close_price for r in rows if r.close_price > 0]
    highs = [r.high_price for r in rows if r.high_price > 0]
    lows = [r.low_price for r in rows if r.low_price > 0]
    volumes = [r.volume for r in rows]
    ois = [r.open_interest for r in rows]

    if not closes:
        return tech

    latest_close = closes[-1]

    # ---- 均线 ----
    for period in [5, 10, 20, 60]:
        ma_val = _ma(closes, period)
        if ma_val:
            tech[f"MA{period}"] = round(ma_val, 2)
            tech[f"price_vs_MA{period}"] = round((latest_close - ma_val) / ma_val * 100, 2)

    # ---- 均线排列 ----
    if all(k in tech for k in ["MA5", "MA10", "MA20", "MA60"]):
        if tech["MA5"] > tech["MA10"] > tech["MA20"] > tech["MA60"]:
            tech["ma_alignment"] = "多头排列(强势)"
        elif tech["MA5"] < tech["MA10"] < tech["MA20"] < tech["MA60"]:
            tech["ma_alignment"] = "空头排列(弱势)"
        elif abs(tech["MA5"] - tech["MA20"]) / tech["MA20"] * 100 < 1.0:
            tech["ma_alignment"] = "均线粘合(即将选择方向)"
        else:
            tech["ma_alignment"] = "交叉缠绕(震荡格局)"

    # ---- 支撑/压力 ----
    if "MA20" in tech:
        tech["support_MA20"] = tech["MA20"]
    if "MA60" in tech:
        tech["support_MA60"] = tech["MA60"]
    tech["recent_high_20d"] = round(_high(highs, 20), 2) if len(highs) >= 20 else (round(max(highs), 2) if highs else 0)
    tech["recent_low_20d"] = round(_low(lows, 20), 2) if len(lows) >= 20 else (round(min(lows), 2) if lows else 0)

    # ---- 价格在均线上方/下方数量 ----
    above_count = 0
    for k in ["MA5", "MA10", "MA20", "MA60"]:
        if k in tech and closes[-1] > tech[k]:
            above_count += 1
    tech["price_above_mas"] = f"{above_count}/4"

    # ---- 趋势通道 ----
    if len(closes) >= 20:
        high20 = _high(highs, 20)
        low20 = _low(lows, 20)
        if high20 and low20 and high20 != low20:
            tech["price_in_channel"] = round((closes[-1] - low20) / (high20 - low20) * 100, 1)

    # ---- 连续涨跌天数 ----
    consecutive_up = 0
    consecutive_down = 0
    for i in range(len(closes) - 1, 0, -1):
        if closes[i] > closes[i - 1]:
            if consecutive_down == 0:
                consecutive_up += 1
            else:
                break
        elif closes[i] < closes[i - 1]:
            if consecutive_up == 0:
                consecutive_down += 1
            else:
                break
        else:
            break
    tech["consecutive_up_days"] = consecutive_up
    tech["consecutive_down_days"] = consecutive_down

    # ---- 成交量分析 ----
    if len(volumes) >= 5:
        recent_vol = volumes[-5:]
        avg_vol_20 = sum(volumes[-20:]) / min(20, len(volumes)) if len(volumes) >= 20 else sum(volumes) / len(volumes)
        tech["volume_ratio"] = round(sum(recent_vol) / 5 / avg_vol_20, 2) if avg_vol_20 else 1.0

    # ---- OI变化率(近5日) ----
    if len(ois) >= 6:
        oi_5d_chg = ois[-1] - ois[-6]
        tech["oi_5d_change"] = oi_5d_chg

    # ---- 波动点检测 + 短期趋势线 ----
    if len(closes) >= 10:
        _detect_short_trends(tech, highs, lows, closes, volumes, ois)

    return tech


def _find_pivots(values: list, window: int = 2) -> list:
    """找局部极值点,返回 [(index, value, 'high'|'low'), ...]"""
    pivots = []
    for i in range(window, len(values) - window):
        left = values[i - window: i]
        right = values[i + 1: i + 1 + window]
        if all(values[i] > x for x in left) and all(values[i] > x for x in right):
            pivots.append((i, values[i], "high"))
        if all(values[i] < x for x in left) and all(values[i] < x for x in right):
            pivots.append((i, values[i], "low"))
    return pivots


def _detect_short_trends(tech: dict, highs: list, lows: list, closes: list, volumes: list, ois: list):
    """检测近期的短期趋势线和形态"""
    n = len(closes)
    recent = min(20, n)

    # 找摆动高低点
    high_pivots = _find_pivots(highs[-recent:], window=2)
    low_pivots = _find_pivots(lows[-recent:], window=2)

    # 提取近10日的多个低点，检测上升趋势线
    recent_lows = []
    recent_highs = []
    for idx, val, pt in low_pivots:
        if pt == "low":
            recent_lows.append((idx, val))
    for idx, val, pt in high_pivots:
        if pt == "high":
            recent_highs.append((idx, val))

    # ----- 检测上升趋势线：至少2个抬高低点 -----
    if len(recent_lows) >= 2:
        # 按顺序取最后几个低点
        recent_lows_sorted = sorted(recent_lows, key=lambda x: x[0])
        if len(recent_lows_sorted) >= 3:
            recent_lows_sorted = recent_lows_sorted[-3:]

        # 检测低点是否逐级抬高
        low_vals = [p[1] for p in recent_lows_sorted]
        if len(low_vals) >= 2 and all(low_vals[i] < low_vals[i + 1] for i in range(len(low_vals) - 1)):
            # 低点抬高 = 上升趋势线
            p1, p2 = recent_lows_sorted[0], recent_lows_sorted[-1]
            duration = p2[0] - p1[0]
            if duration >= 3:
                slope = (p2[1] - p1[1]) / duration
                # 当前价格相对趋势线的位置
                extrapolated = p2[1] + slope * (recent - 1 - p2[0])
                if extrapolated > 0:
                    distance_pct = (closes[-1] - extrapolated) / extrapolated * 100
                    tech["ascending_trendline"] = (
                        f"{duration}天上升趋势线(低点{p1[1]:.1f}→{p2[1]:.1f}), "
                        f"当前价距趋势线{distance_pct:+.1f}%"
                    )
                    if closes[-1] < extrapolated * 0.99:
                        tech["trendline_break"] = f"价格跌破上升趋势线({distance_pct:+.1f}%)"

    # ----- 检测下降趋势线：至少2个降低高点 -----
    if len(recent_highs) >= 2:
        recent_highs_sorted = sorted(recent_highs, key=lambda x: x[0])
        if len(recent_highs_sorted) >= 3:
            recent_highs_sorted = recent_highs_sorted[-3:]

        high_vals = [p[1] for p in recent_highs_sorted]
        if len(high_vals) >= 2 and all(high_vals[i] > high_vals[i + 1] for i in range(len(high_vals) - 1)):
            p1, p2 = recent_highs_sorted[0], recent_highs_sorted[-1]
            duration = p2[0] - p1[0]
            if duration >= 3:
                slope = (p2[1] - p1[1]) / duration
                extrapolated = p2[1] + slope * (recent - 1 - p2[0])
                if extrapolated > 0:
                    distance_pct = (closes[-1] - extrapolated) / extrapolated * 100
                    tech["descending_trendline"] = (
                        f"{duration}天下降趋势线(高点{p1[1]:.1f}→{p2[1]:.1f}), "
                        f"当前价距趋势线{distance_pct:+.1f}%"
                    )
                    if closes[-1] > extrapolated * 1.01:
                        tech["trendline_break"] = f"价格突破下降趋势线({distance_pct:+.1f}%)"

    # ----- 检测5日/10日微型趋势 -----
    for window in [5, 10]:
        if n >= window:
            segment = closes[-window:]
            up_count = sum(1 for i in range(1, len(segment)) if segment[i] > segment[i - 1])
            down_count = sum(1 for i in range(1, len(segment)) if segment[i] < segment[i - 1])
            chg = (segment[-1] - segment[0]) / segment[0] * 100 if segment[0] else 0

            if up_count >= window * 0.7:
                tech[f"micro_trend_{window}d"] = f"连续上涨型({chg:+.2f}%, {up_count}/{window-1}日收阳)"
            elif down_count >= window * 0.7:
                tech[f"micro_trend_{window}d"] = f"连续下跌型({chg:+.2f}%, {down_count}/{window-1}日收阴)"
            elif abs(chg) < 0.5:
                tech[f"micro_trend_{window}d"] = f"横盘整理({chg:+.2f}%)"

    # ----- V型反转检测 -----
    if n >= 10:
        segment = closes[-10:]
        min_idx = segment.index(min(segment))
        max_idx = segment.index(max(segment))
        if min_idx > 0 and min_idx < 9:
            left_chg = (segment[min_idx] - segment[0]) / segment[0] * 100
            right_chg = (segment[-1] - segment[min_idx]) / segment[min_idx] * 100
            if left_chg < -1.5 and right_chg > 1.5:
                tech["pattern"] = f"V型反转(先跌{left_chg:.2f}%后涨{right_chg:.2f}%, 低点在第{min_idx+1}天)"
        if max_idx > 0 and max_idx < 9:
            left_chg = (segment[max_idx] - segment[0]) / segment[0] * 100
            right_chg = (segment[-1] - segment[max_idx]) / segment[max_idx] * 100
            if left_chg > 1.5 and right_chg < -1.5:
                tech["pattern"] = f"倒V反转(先涨{left_chg:.2f}%后跌{right_chg:.2f}%, 高点在第{max_idx+1}天)"

    # ----- 突破近期高点/低点 -----
    if n >= 10:
        prev_high = max(highs[-11:-1])
        prev_low = min(lows[-11:-1])
        if closes[-1] > prev_high:
            tech["breakout"] = f"今日突破近10日高点({prev_high:.1f})"
        if closes[-1] < prev_low:
            tech["breakout"] = f"今日跌破近10日低点({prev_low:.1f})"


# ============================================================
# 多周期数据提取
# ============================================================

def _get_period_summary(contract_code: str, start: date, end: date, db) -> dict:
    rows = (
        db.query(ContractOI)
        .filter(ContractOI.contract_code == contract_code.upper(),
                ContractOI.trade_date >= start, ContractOI.trade_date <= end)
        .order_by(ContractOI.trade_date.asc())
        .all()
    )
    if not rows or len(rows) < 2:
        return {}

    first, last = rows[0], rows[-1]
    oi_chg = last.open_interest - first.open_interest
    pct = (last.close_price - first.close_price) / first.close_price * 100 if first.close_price else 0
    total_vol = sum(r.volume for r in rows)

    # 量价定性
    if pct > 0.5 and oi_chg > 0:
        vp = "增仓上涨"
    elif pct < -0.5 and oi_chg > 0:
        vp = "增仓下跌"
    elif pct > 0.5 and oi_chg < 0:
        vp = "减仓上涨(空头离场)"
    elif pct < -0.5 and oi_chg < 0:
        vp = "减仓下跌(多头离场)"
    else:
        vp = "震荡"

    return {
        "start": str(start), "end": str(end),
        "price_chg": f"{pct:+.2f}%",
        "oi_chg": f"{oi_chg:+}",
        "volume": total_vol,
        "vp_signal": vp,
        "days": len(rows),
    }


# ============================================================
# 主计算引擎
# ============================================================

def _compute_indicators(contract_code: str, start_date: date, end_date: date) -> dict:
    db = SessionLocal()
    try:
        indicators = {}

        # ---- 技术指标 ----
        tech = _compute_technical_indicators(contract_code, db)
        indicators["tech"] = tech

        # ---- 多周期数据 (短→中→长) ----
        today = date.today()
        indicators["period_short"] = _get_period_summary(contract_code, start_date, end_date, db)
        indicators["period_20d"] = _get_period_summary(contract_code, today - timedelta(days=30), today, db)
        indicators["period_mid"] = _get_period_summary(contract_code, today - timedelta(days=90), today, db)
        indicators["period_long"] = _get_period_summary(contract_code, today - timedelta(days=180), today, db)

        # ---- 多周期方向判断 (20日是关键锚点) ----
        short_pct = float(indicators["period_short"].get("price_chg", "0").strip("%+")) if indicators["period_short"] else 0
        d20_pct = float(indicators["period_20d"].get("price_chg", "0").strip("%+")) if indicators["period_20d"] else 0
        mid_pct = float(indicators["period_mid"].get("price_chg", "0").strip("%+")) if indicators["period_mid"] else 0
        long_pct = float(indicators["period_long"].get("price_chg", "0").strip("%+")) if indicators["period_long"] else 0

        short_dir = "多头" if short_pct > 0.3 else ("空头" if short_pct < -0.3 else "震荡")
        d20_dir = "多头" if d20_pct > 0.5 else ("空头" if d20_pct < -0.5 else "震荡")
        mid_dir = "多头" if mid_pct > 0.5 else ("空头" if mid_pct < -0.5 else "震荡")
        long_dir = "多头" if long_pct > 1.0 else ("空头" if long_pct < -1.0 else "震荡")

        # 关键判断：短期 vs 20日趋势
        if short_dir != d20_dir and d20_dir != "震荡":
            indicators["trend_context"] = f"方向背离: 20日{d20_dir}({d20_pct:+.1f}%) vs 本期{short_dir}({short_pct:+.1f}%)"
        else:
            indicators["trend_context"] = f"方向一致: 20日{d20_dir}({d20_pct:+.1f}%) vs 本期{short_dir}({short_pct:+.1f}%)"

        indicators["triple_direction"] = f"长期{long_dir}({long_pct:+.1f}%) → 中期{mid_dir}({mid_pct:+.1f}%) → 近20日{d20_dir}({d20_pct:+.1f}%) → 本期{short_dir}({short_pct:+.1f}%)"

        # 一致性评分 (以20日方向为锚)
        consistency = 0
        if long_dir == d20_dir: consistency += 3
        if d20_dir == short_dir: consistency += 3
        if mid_dir == d20_dir: consistency += 2
        if tech.get("ma_alignment") in ("多头排列(强势)", "空头排列(弱势)"): consistency += 2
        indicators["consistency_score"] = consistency

        # ---- 机构数据 ----
        latest_date_row = (
            db.query(MemberPosition.trade_date)
            .filter(MemberPosition.symbol == contract_code.upper(),
                    MemberPosition.trade_date >= start_date, MemberPosition.trade_date <= end_date)
            .order_by(MemberPosition.trade_date.desc())
            .first()
        )

        earliest_date_row = (
            db.query(MemberPosition.trade_date)
            .filter(MemberPosition.symbol == contract_code.upper(),
                    MemberPosition.trade_date >= start_date, MemberPosition.trade_date <= end_date)
            .order_by(MemberPosition.trade_date.asc())
            .first()
        )

        if latest_date_row:
            latest_date = latest_date_row[0]
            latest_members = (
                db.query(MemberPosition)
                .filter(MemberPosition.symbol == contract_code.upper(), MemberPosition.trade_date == latest_date)
                .all()
            )

            earliest_members = []
            if earliest_date_row:
                earliest_members = (
                    db.query(MemberPosition)
                    .filter(MemberPosition.symbol == contract_code.upper(), MemberPosition.trade_date == earliest_date_row[0])
                    .all()
                )

            total_long = sum(m.long_position for m in latest_members)
            total_short = sum(m.short_position for m in latest_members)
            indicators["total_long"] = total_long
            indicators["total_short"] = total_short
            indicators["long_short_ratio"] = round(total_long / total_short, 3) if total_short else 1.0
            indicators["net_total"] = total_long - total_short

            net_long_n = sum(1 for m in latest_members if m.net_position > 0)
            net_short_n = sum(1 for m in latest_members if m.net_position < 0)
            total_n = net_long_n + net_short_n
            indicators["divergence"] = round(1 - abs(net_long_n - net_short_n) / total_n, 2) if total_n else 0

            # 集中度
            s_long = sorted([m.long_position for m in latest_members], reverse=True)
            s_short = sorted([m.short_position for m in latest_members], reverse=True)
            indicators["top5_long_pct"] = round(sum(s_long[:5]) / total_long * 100, 1) if total_long else 0
            indicators["top5_short_pct"] = round(sum(s_short[:5]) / total_short * 100, 1) if total_short else 0

            # 正指分析
            correct_seats, contrary_seats = [], []
            for m in latest_members:
                prof = INSTITUTION_PROFILES.get(m.member_name, {})
                ind = prof.get("indicator", "")
                if "正指" in ind:
                    correct_seats.append({"name": m.member_name, "net": m.net_position, "chg": m.net_change})
                if "反指" in ind:
                    contrary_seats.append({"name": m.member_name, "net": m.net_position, "chg": m.net_change})

            indicators["correct_seats"] = correct_seats
            indicators["contrary_seats"] = contrary_seats
            if correct_seats:
                nets = [s["net"] for s in correct_seats]
                indicators["correct_consensus"] = "一致偏多" if sum(1 for n in nets if n > 0) >= len(nets) * 0.7 else (
                    "一致偏空" if sum(1 for n in nets if n < 0) >= len(nets) * 0.7 else "分歧"
                )

            # 期间变化
            earliest_map = {m.member_name: m for m in earliest_members}
            period_changes = []
            for m in latest_members:
                e = earliest_map.get(m.member_name)
                if e:
                    period_changes.append({
                        "name": m.member_name,
                        "net_chg": m.net_position - e.net_position,
                        "long_chg": m.long_position - e.long_position,
                        "short_chg": m.short_position - e.short_position,
                    })
            indicators["period_changes"] = period_changes

            # 异常检测
            alerts = []
            for cs in contrary_seats:
                hist = (
                    db.query(MemberPosition.net_position)
                    .filter(MemberPosition.symbol == contract_code.upper(),
                            MemberPosition.member_name == cs["name"],
                            MemberPosition.trade_date >= end_date - timedelta(days=60))
                    .all()
                )
                vals = [h[0] for h in hist if h[0] is not None]
                if vals and len(vals) >= 5:
                    abs_max = max(abs(v) for v in vals)
                    if abs(cs["net"]) >= abs_max * 0.95:
                        alerts.append(f"反指{cs['name']}净持仓达60日极值({cs['net']})，警惕反转")

            # 多翻空/空翻多检测
            for m in latest_members:
                prev_rows = (
                    db.query(MemberPosition.net_position)
                    .filter(MemberPosition.symbol == contract_code.upper(),
                            MemberPosition.member_name == m.member_name,
                            MemberPosition.trade_date >= end_date - timedelta(days=7),
                            MemberPosition.trade_date <= end_date)
                    .order_by(MemberPosition.trade_date.asc())
                    .all()
                )
                if len(prev_rows) >= 2:
                    first_net = prev_rows[0][0]
                    last_net = prev_rows[-1][0]
                    if first_net is not None and last_net is not None:
                        if first_net > abs(last_net) * 0.3 > 0 > last_net:
                            alerts.append(f"席位转向: {m.member_name} 近5日多翻空")
                        elif first_net < 0 and last_net > abs(first_net) * 0.3:
                            alerts.append(f"席位转向: {m.member_name} 近5日空翻多")

            indicators["alerts"] = alerts

            # 基差
            basis = _estimate_basis(contract_code, end_date, db)
            if basis:
                indicators["basis"] = basis

            # 详细机构数据(用于传给AI)
            indicators["latest_members"] = [
                {"name": m.member_name, "long": m.long_position, "long_chg": m.long_change,
                 "short": m.short_position, "short_chg": m.short_change, "net": m.net_position}
                for m in latest_members[:25]
            ]

        return indicators
    finally:
        db.close()


def _estimate_basis(contract_code: str, ref_date: date, db) -> dict | None:
    try:
        row = (
            db.query(ContractOI)
            .filter(ContractOI.contract_code == contract_code.upper(), ContractOI.trade_date <= ref_date)
            .order_by(ContractOI.trade_date.desc())
            .first()
        )
        if not row or not row.settle_price:
            return None
        settle = row.settle_price

        prefix = re.match(r"^([A-Z]+)", contract_code.upper())
        if not prefix:
            return None

        nearby = (
            db.query(ContractOI)
            .filter(ContractOI.contract_code.like(f"{prefix.group(1)}%"),
                    ContractOI.contract_code != contract_code.upper(),
                    ContractOI.trade_date == row.trade_date)
            .order_by(ContractOI.contract_code)
            .first()
        )

        if nearby and nearby.settle_price:
            spread = settle - nearby.settle_price
            spread_pct = spread / nearby.settle_price * 100
            alert = "正常"
            if abs(spread_pct) > 3:
                alert = f"价差异常({spread_pct:+.2f}%)可能逼仓"
            elif abs(spread_pct) > 1.5:
                alert = f"价差偏大({spread_pct:+.2f}%)"
            return {"settle": settle, "nearby_code": nearby.contract_code, "nearby_price": nearby.settle_price,
                    "spread": round(spread, 1), "spread_pct": round(spread_pct, 2), "alert": alert}
    except Exception:
        pass
    return None


# ============================================================
# 构建AI数据摘要
# ============================================================

def _build_ai_data_summary(contract_code: str, start_date: date, end_date: date, ind: dict) -> str:
    lines = [f"=== {contract_code} 分析数据包 (持仓数据为核心) ===\n"]

    # ---- 持仓数据放最前面 ----
    if ind.get("total_long"):
        lines.append(f"【持仓结构】")
        lines.append(f"  多头总量: {ind['total_long']}  空头总量: {ind['total_short']}")
        lines.append(f"  多空比: {ind['long_short_ratio']}  净持仓: {ind['net_total']:+}")
        lines.append(f"  多空分歧度: {ind.get('divergence',0):.2f} (0=一致, 1=极度分歧)")
        lines.append(f"  Top5集中度: 多头{ind.get('top5_long_pct',0)}%  空头{ind.get('top5_short_pct',0)}%")

    if ind.get("correct_seats"):
        lines.append(f"\n【正指席位】共识: {ind.get('correct_consensus','?')}")
        for s in ind["correct_seats"]:
            lines.append(f"  {s['name']}: 净{s['net']:+}  日变{s.get('chg',0):+}")
    if ind.get("contrary_seats"):
        lines.append(f"\n【反指席位(警惕)】")
        for s in ind["contrary_seats"]:
            lines.append(f"  {s['name']}: 净{s['net']:+}  日变{s.get('chg',0):+}")

    if ind.get("latest_members"):
        lines.append(f"\n【机构持仓明细(TOP20)】")
        for m in ind["latest_members"][:20]:
            prof = INSTITUTION_PROFILES.get(m["name"], {})
            tag = "正指" if "正指" in prof.get("indicator", "") else ("反指" if "反指" in prof.get("indicator", "") else "")
            tag_str = f" [{tag}]" if tag else ""
            lines.append(
                f"  {m['name']}{tag_str}  多:{m['long']}({m['long_chg']:+})  "
                f"空:{m['short']}({m['short_chg']:+})  净:{m['net']:+}"
            )

    if ind.get("period_changes"):
        top = sorted(ind["period_changes"], key=lambda x: abs(x["net_chg"]), reverse=True)[:8]
        lines.append(f"\n【期间净变化TOP8】")
        for pc in top:
            lines.append(f"  {pc['name']}: 净{pc['net_chg']:+} (多{pc['long_chg']:+} 空{pc['short_chg']:+})")

    # ---- 多周期数据 ----
    lines.append(f"\n【多周期背景】")
    lines.append(f"  完整链条: {ind.get('triple_direction', '?')}")
    for label, key in [("本期(用户所选)", "period_short"), ("近20日", "period_20d"),
                        ("中期(90日)", "period_mid"), ("长期(180日)", "period_long")]:
        p = ind.get(key, {})
        if p:
            lines.append(f"  {label}: 涨跌{p.get('price_chg','?')}  OI{p.get('oi_chg','?')}  {p.get('vp_signal','?')}")
    lines.append(f"  一致性评分: {ind.get('consistency_score', '?')}/10")
    if ind.get("trend_context"):
        lines.append(f"  注: {ind['trend_context']}")

    # ---- 技术面放最后 ----
    tech = ind.get("tech", {})
    if tech:
        lines.append(f"\n【技术指标(辅助)】")
        lines.append(f"  均线: {tech.get('ma_alignment', '?')}")
        lines.append(f"  MA5={tech.get('MA5','?')} MA10={tech.get('MA10','?')} MA20={tech.get('MA20','?')} MA60={tech.get('MA60','?')}")
        for key, label in [
            ("ascending_trendline", "上升趋势线"), ("descending_trendline", "下降趋势线"),
            ("trendline_break", "趋势线突破"), ("breakout", "突破信号"),
            ("pattern", "技术形态"),
            ("micro_trend_5d", "5日趋势"), ("micro_trend_10d", "10日趋势"),
        ]:
            if tech.get(key):
                lines.append(f"  {label}: {tech[key]}")

    # ---- 预警 ----
    if ind.get("alerts"):
        lines.append(f"\n【预警】")
        for a in ind["alerts"]:
            lines.append(f"  {a}")

    # ---- 基差 ----
    if ind.get("basis"):
        b = ind["basis"]
        lines.append(f"\n【基差】{b['nearby_code']}价差{b['spread']}({b['spread_pct']:+.2f}%) {b['alert']}")

    # ---- 速查 ----
    lines.append(f"\n【机构速查】")
    for name, prof in INSTITUTION_PROFILES.items():
        lines.append(f"  {name}: {prof['indicator']}")

    lines.append(f"\n--- 以上: 持仓数据为核心，技术面仅辅助验证 ---")

    return "\n".join(lines)


# ============================================================
# AI调用
# ============================================================

def _resolve_date_range(days: int, start: str, end: str) -> tuple:
    today = date.today()
    if start and end:
        return date.fromisoformat(start), date.fromisoformat(end), (date.fromisoformat(end) - date.fromisoformat(start)).days
    d = days if days else 30
    return today - timedelta(days=d), today, d


def _period_label(days: int) -> str:
    return {7: "近一周", 14: "近两周", 30: "近一个月", 90: "近一个季度", 180: "近半年", 365: "近一年"}.get(days, f"近{days}天")


async def generate_analysis(symbol: str, variety: str = None, days: int = None,
                            start_date: str = None, end_date: str = None) -> str:
    start, end, period_days = _resolve_date_range(days, start_date, end_date)
    label = _period_label(period_days)
    contract_code = symbol.upper()

    indicators = _compute_indicators(contract_code, start, end)
    data_summary = _build_ai_data_summary(contract_code, start, end, indicators)

    ai_config = get_ai_config()
    api_key = ai_config.get("api_key", "")
    base_url = ai_config.get("base_url", "https://api.openai.com/v1")
    model = ai_config.get("model", "gpt-4o-mini")
    temperature = ai_config.get("temperature", 0.3)
    max_tokens = ai_config.get("max_tokens", 4000)

    if not api_key:
        return f"[AI分析未配置] 请先在设置页面填写 API Key\n\n{label} 数据摘要:\n{data_summary}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",
             "content": f"分析 {contract_code}【{label}】({start}~{end})\n\n已预处理数据:\n{data_summary}\n\n请按6段格式输出报告。"},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{base_url.rstrip('/')}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as e:
        return f"[AI分析失败] HTTP {e.response.status_code}"
    except Exception as e:
        return f"[AI分析失败] {str(e)}"


# ============================================================
# 存储
# ============================================================

def save_analysis(symbol: str, content: str, period: str = "1w"):
    cfg = get_ai_config()
    db = SessionLocal()
    try:
        db.add(AnalysisReport(symbol=symbol, report_date=date.today(), period=period, content=content, model_used=cfg.get("model", "unknown")))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"保存失败: {e}")
    finally:
        db.close()


def get_latest_analysis(symbol: str) -> dict | None:
    db = SessionLocal()
    try:
        r = db.query(AnalysisReport).filter(AnalysisReport.symbol == symbol).order_by(AnalysisReport.created_at.desc()).first()
        if r:
            return {"symbol": r.symbol, "date": str(r.report_date), "period": r.period, "content": r.content,
                    "model": r.model_used, "created_at": str(r.created_at)}
        return None
    finally:
        db.close()


def get_analysis_history(symbol: str, limit: int = 20) -> list:
    db = SessionLocal()
    try:
        return [
            {"symbol": r.symbol, "date": str(r.report_date), "period": r.period, "content": r.content, "model": r.model_used}
            for r in db.query(AnalysisReport).filter(AnalysisReport.symbol == symbol)
                   .order_by(AnalysisReport.created_at.desc()).limit(limit).all()
        ]
    finally:
        db.close()


FOLLOWUP_PROMPT = """你是一位期货持仓分析师，正在和用户讨论一份已经生成的持仓分析报告。

规则：
- 直接回答问题，不啰嗦，不重复报告里已有的内容
- 如果问具体数据，用报告中已有的数字回答
- 如果问看法，基于已有的持仓数据给出推理
- 回答控制在200字以内
- 不要用Markdown格式"""


async def chat_followup(contract_code: str, question: str, analysis_context: str = "", history: list = None):
    ai_config = get_ai_config()
    api_key = ai_config.get("api_key", "")
    base_url = ai_config.get("base_url", "https://api.openai.com/v1")
    model = ai_config.get("model", "gpt-4o-mini")

    if not api_key:
        return "未配置 AI API Key"

    messages = [{"role": "system", "content": FOLLOWUP_PROMPT}]

    if analysis_context:
        messages.append({"role": "assistant", "content": f"[分析报告]\n{analysis_context[:3000]}"})

    if history:
        for h in history[-10:]:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})

    messages.append({"role": "user", "content": question})

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "temperature": 0.3, "max_tokens": 800},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[追问失败] {str(e)[:100]}"
