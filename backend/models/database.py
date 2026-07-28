from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Text, Index
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from backend.config_loader import get_db_path

Base = declarative_base()


class _LazySession:
    _maker = None

    @classmethod
    def _get_maker(cls):
        if cls._maker is None:
            engine = create_engine(f"sqlite:///{get_db_path()}", echo=False, connect_args={"check_same_thread": False})
            cls._maker = sessionmaker(bind=engine)
        return cls._maker

    def __call__(self, **kwargs):
        return self._get_maker()(**kwargs)


SessionLocal = _LazySession()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ContractOI(Base):
    """单个合约的持仓量和成交量日线数据"""
    __tablename__ = "contract_oi"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(Date, nullable=False, index=True)
    contract_code = Column(String(20), nullable=False, index=True)

    open_price = Column(Float, default=0.0)
    high_price = Column(Float, default=0.0)
    low_price = Column(Float, default=0.0)
    close_price = Column(Float, default=0.0)
    settle_price = Column(Float, default=0.0)

    volume = Column(Integer, default=0)
    open_interest = Column(Integer, default=0)
    oi_change = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_contract_date_code", "trade_date", "contract_code", unique=True),
    )


class DailyPosition(Base):
    """品种级别的每日持仓排名汇总"""
    __tablename__ = "daily_positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(Date, nullable=False, index=True)
    symbol = Column(String(50), nullable=False)
    exchange = Column(String(20), nullable=False)
    variety_name = Column(String(50))

    volume = Column(Integer, default=0)
    open_interest = Column(Integer, default=0)
    long_position = Column(Integer, default=0)
    short_position = Column(Integer, default=0)
    net_position = Column(Integer, default=0)

    top5_long = Column(Integer, default=0)
    top5_short = Column(Integer, default=0)
    top10_long = Column(Integer, default=0)
    top10_short = Column(Integer, default=0)
    top20_long = Column(Integer, default=0)
    top20_short = Column(Integer, default=0)

    long_change = Column(Integer, default=0)
    short_change = Column(Integer, default=0)
    net_change = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_trade_date_symbol", "trade_date", "symbol", unique=True),
    )


class MemberPosition(Base):
    """品种级别的各机构持仓明细"""
    __tablename__ = "member_positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(Date, nullable=False, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    member_name = Column(String(100), nullable=False)

    long_position = Column(Integer, default=0)
    long_change = Column(Integer, default=0)
    short_position = Column(Integer, default=0)
    short_change = Column(Integer, default=0)
    net_position = Column(Integer, default=0)
    net_change = Column(Integer, default=0)

    volume = Column(Integer, default=0)
    volume_change = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_member_date_symbol", "trade_date", "symbol", "member_name", unique=True),
    )


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False, index=True)
    report_date = Column(Date, nullable=False, index=True)
    period = Column(String(20), default="1w")
    content = Column(Text, nullable=False)
    model_used = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    engine = create_engine(f"sqlite:///{get_db_path()}", echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
