import os
import re
import yaml

_CONFIG = None

# 品种代码 -> 中文名称
CODE_TO_VARIETY = {
    "rb": "螺纹钢", "hc": "热卷", "ss": "不锈钢", "wr": "线材",
    "i": "铁矿石", "j": "焦炭", "jm": "焦煤",
    "m": "豆粕", "a": "豆一", "b": "豆二", "y": "豆油", "p": "棕榈油",
    "c": "玉米", "cs": "玉米淀粉", "l": "塑料", "pp": "聚丙烯",
    "v": "PVC", "eg": "乙二醇", "eb": "苯乙烯", "pg": "液化气",
    "sc": "原油", "fu": "燃料油", "bu": "沥青", "ru": "橡胶",
    "cu": "沪铜", "al": "沪铝", "zn": "沪锌", "pb": "沪铅",
    "ni": "沪镍", "sn": "沪锡", "au": "沪金", "ag": "沪银",
    "ta": "PTA", "ma": "甲醇", "fg": "玻璃", "sa": "纯碱",
    "rm": "菜粕", "oi": "菜油", "cf": "棉花", "sr": "白糖",
    "zc": "动力煤", "sm": "硅锰", "sf": "硅铁",
    "if": "沪深300", "ic": "中证500", "im": "中证1000", "ih": "上证50",
    "t": "10年国债", "tf": "5年国债", "ts": "2年国债",
}


def load_config(path: str = None) -> dict:
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG

    if path is None:
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")

    with open(path, "r", encoding="utf-8") as f:
        _CONFIG = yaml.safe_load(f)

    ai_key = _CONFIG.get("ai", {}).get("api_key", "")
    if ai_key.startswith("${") and ai_key.endswith("}"):
        env_var = ai_key[2:-1]
        _CONFIG["ai"]["api_key"] = os.environ.get(env_var, "")

    _normalize_contracts(_CONFIG)

    return _CONFIG


def _normalize_contracts(config: dict):
    contracts = config.get("contracts", [])
    for c in contracts:
        code = c.get("code", "").upper()
        c["code"] = code

        if not c.get("variety"):
            prefix = re.match(r"^([A-Z]+)", code)
            if prefix:
                c["variety"] = CODE_TO_VARIETY.get(prefix.group(1).lower(), code)


def get_contracts() -> list:
    config = load_config()
    return config.get("contracts", [])


def get_variety_for_code(code: str) -> str:
    config = load_config()
    for c in config.get("contracts", []):
        if c["code"].upper() == code.upper():
            return c.get("variety", code)
    prefix = re.match(r"^([A-Z]+)", code.upper())
    if prefix:
        return CODE_TO_VARIETY.get(prefix.group(1).lower(), code)
    return code


def get_contract_codes() -> list:
    return [c["code"] for c in get_contracts()]


def get_tracked_varieties() -> list:
    seen = set()
    result = []
    for c in get_contracts():
        v = c.get("variety", c["code"])
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result


def get_ai_config() -> dict:
    config = load_config()
    return config.get("ai", {})


def get_fetcher_config() -> dict:
    config = load_config()
    return config.get("fetcher", {})


_CONFIG_PATH = None


def _config_path():
    global _CONFIG_PATH
    if _CONFIG_PATH is None:
        _CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
    return _CONFIG_PATH


def save_config(data: dict):
    global _CONFIG
    path = _config_path()
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    _CONFIG = data
    _normalize_contracts(_CONFIG)


def reload_config():
    global _CONFIG
    _CONFIG = None
    return load_config()


def get_db_path() -> str:
    config = load_config()
    db_path = config.get("database", {}).get("path", "data/futures.db")
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db_path)
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    return db_path
