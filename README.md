# 期货持仓分析系统

基于 AKShare + LLM 的期货持仓分析工具，自动采集合约 OI 和机构持仓数据，AI 智能研判主力动向。

## 功能

- 关注任意期货合约，追踪单合约 OI + 价格走势 + 量价关系
- 每日抓取会员多空持仓排名，辨识中信/永安/国泰等机构的交易风格
- 正指/反指席位标注，席位转向预警
- 多周期持仓验证（短期/中期/长期），趋势线检测
- AI 生成持仓驱动力分析、席位追踪、综合研判报告
- 分析后支持继续追问
- 每日收盘后定时自动采集

## 截图

![仪表盘](screenshots/dashboard.png)
![分析详情](screenshots/detail.png)

## 快速开始

```bash
# 1. 安装依赖
pip install -r backend/requirements.txt
cd frontend && npm install && npx vite build && cd ..

# 2. 复制配置文件
cp config.example.yaml config.yaml

# 3. 双击 start.bat 启动（Windows）或
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# 4. 浏览器打开 http://localhost:8000
#    在设置页面填写合约代码和 AI API Key 即可使用
```

## 技术栈

| 数据 | 后端 | 前端 | 定时 | AI |
|---|---|---|---|---|
| AKShare + Sina | FastAPI + SQLite | Vue3 + ECharts | APScheduler | OpenAI 兼容接口 |

## 项目结构

```
backend/
├── main.py              FastAPI 入口
├── fetcher/             数据采集（合约OI、机构持仓）
├── models/              数据库模型（SQLite）
├── analyzer/            AI 分析引擎（指标计算 + LLM 调用）
├── api/                 REST 接口
└── scheduler.py         定时任务
frontend/
├── src/views/           Dashboard / Detail / Settings
└── src/api/             前端 API 层
config.example.yaml      配置模板
start.bat                Windows 一键启动
```

## 注意事项

- `config.yaml` 包含 API Key，已加入 `.gitignore`，不会上传
- 使用前复制 `config.example.yaml` 为 `config.yaml` 并填写配置
- 或在 Web 设置页面直接填，会自动写入 `config.yaml`
