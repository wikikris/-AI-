# 期货持仓分析系统

基于 AKShare + LLM 的期货持仓分析工具。自动采集合约 OI 和机构持仓数据，AI 智能研判主力动向。

## 更新日志

### v2.1 (2026-07)

- **K线图替代量价折线** — 蜡烛图 + MA5/MA10/MA20 均线 + 成交量柱，支持滚轮缩放，悬浮显示完整 OHLC + 涨跌差价
- **液态玻璃 UI** — 全界面毛玻璃效果：`backdrop-filter` 多层模糊 + 镜面高光镶边 + 环境光晕 + 层次深度感
- **独立 EXE 打包** — PyInstaller 一键打包为 `FuturesPA.exe`，无需安装 Python/Node.js，双击即用
- **聊天持久化** — 追问内容自动保存到浏览器，切换页面/重启不会丢失
- **仪表盘"聊"按钮** — 直接从首页跳转合约详情页追问 AI
- **分析报告日期范围** — 报告标题显示实际数据区间（如 `2026-06-01 ~ 2026-07-27`）
- **智能预警引擎** — 合约换月检测、席位历史准确率（正指/反指）自动统计
- **分析摘要折叠** — 仪表盘默认显示 5 条分析，可展开全部
- **启动脚本优化** — `start.bat` 自动杀掉 8000 端口旧进程

### v2.0

- 初始版本

## 截图

![仪表盘](screenshots/dashboard.png)
![分析详情](screenshots/detail.png)

> 截图非最新版，实际界面已升级为暗色现代化设计。

## 你需要准备

**方式一（推荐）：直接下载 EXE，无需安装任何环境**

从 [GitHub Releases](https://github.com/wikikris/futures-position-AI-analyzer/releases) 下载 `FuturesPA.exe`，双击运行即可。首次启动会自动创建默认配置文件。

> 仅支持 Windows 64 位，约 337MB，自带 Python 运行时 + 所有依赖。

**方式二：从源码运行**

- **Python 3.10+**（[下载](https://www.python.org/downloads/)）
- **Node.js 18+**（[下载](https://nodejs.org/)）
- **Git**（[下载](https://git-scm.com/downloads)），或者直接从 GitHub 网页下载 ZIP

## 从源码安装

### 第一步：下载项目

打开终端（Windows 按 `Win+R` 输入 `powershell`），找一个你放项目的目录：

```powershell
# 方式一：用 Git 克隆（推荐）
git clone https://github.com/wikikris/futures-position-AI-analyzer.git
cd futures-position-AI-analyzer

# 方式二：或者直接从 GitHub 网页点 Code → Download ZIP，解压后进入文件夹
```

### 第二步：安装 Python 依赖

```powershell
pip install -r backend/requirements.txt
```

### 第三步：安装前端依赖并构建

```powershell
cd frontend
npm install
npx vite build
cd ..
```

### 第四步：创建配置文件

```powershell
# Windows
copy config.example.yaml config.yaml

# Mac / Linux
cp config.example.yaml config.yaml
```

### 第五步：启动

```powershell
# Windows 直接双击 start.bat

# 或者终端运行：
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

浏览器会自动打开 `http://localhost:8000`。如果没有自动打开，手动访问即可。

### 第六步：配置并开始使用

```powershell
# 安装 PyInstaller
pip install pyinstaller

# 双击 build_exe.bat 或在终端运行：
pyinstaller --name=FuturesPA --onefile --console --add-data="frontend/dist;frontend/dist" --add-data="config.example.yaml;." --collect-data=akshare launcher.py

# 输出: dist\FuturesPA.exe (~337MB)
```

1. 点击顶部 **设置**，填写你的 AI API Key（支持 OpenAI / DeepSeek 等兼容接口）
2. 在 **关注合约** 区域添加你想跟踪的合约，如 `RB2610`、`I2609`
3. 保存后回到仪表盘，点击 **采集数据**
4. 数据采集完成后，点击合约代码进入详情页
5. 选择分析周期（周/月），点击 **分析** 按钮
6. 查看 AI 生成的持仓分析报告，可以继续追问

> 合约代码需要是当前活跃的主力合约，过期合约没有数据。

## 功能

- **K线图** — 蜡烛图 + MA5/MA10/MA20 均线 + 成交量柱，支持鼠标滚轮缩放
- **价格速览** — K线下方展示最新价、涨跌幅、最高/最低、成交量、持仓量、日增仓
- **持仓分析** — 多空持仓走势、机构净持仓排名、机构趋势跟踪
- 正指/反指席位标注，席位转向预警
- **智能预警** — 合约换月检测、持仓集中度预警、席位历史准确率统计
- 多周期持仓验证，趋势线检测
- AI 生成持仓驱动力分析、席位追踪、综合研判报告
- AI 分析后支持聊天式追问
- 每日 16:30 定时自动采集
- **暗色现代化 UI** — 指标卡片、彩色分析摘要、聊天气泡、等宽数字排版

## 技术栈

| 数据 | 后端 | 前端 | 定时 | AI |
|---|---|---|---|---|
| AKShare + Sina | FastAPI + SQLite | Vue3 + ECharts | APScheduler | OpenAI 兼容接口 |

## 常见问题

- 采集数据没反应：检查合约代码是否过期，换成当前活跃合约
- AI 分析没有内容：检查 API Key 是否正确填写
- 页面图表不显示 / 样式异常：按 `Ctrl+Shift+R` 强制刷新浏览器清除缓存
- K线均线不完整：系统已自动扩展数据范围填充 MA，若仍有问题请强制刷新
- EXE 启动后浏览器没打开：手动访问 `http://127.0.0.1:8000`

## 自行打包 EXE

```powershell
pip install pyinstaller
pyinstaller --name=FuturesPA --onefile --console ^
  --add-data="frontend/dist;frontend/dist" ^
  --add-data="config.example.yaml;." ^
  --collect-data=akshare ^
  launcher.py
# 输出: dist\FuturesPA.exe (~337MB)
```

或直接双击 `build_exe.bat`。
