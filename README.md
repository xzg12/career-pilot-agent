<div align="center">

# CareerPilot · 求职管理 Agent

**基于 LangChain + ReAct 范式 + RAG 检索增强的求职管理 AI Agent**

[![Python](https://img.shields.io/badge/Python-3.12+-blue)](https://www.python.org/)
&nbsp;
[![LangChain](https://img.shields.io/badge/LangChain-1.3-green)](https://www.langchain.com/)
&nbsp;
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2-orange)](https://github.com/langchain-ai/langgraph)
&nbsp;
[![Streamlit](https://img.shields.io/badge/Streamlit-1.62-red)](https://streamlit.io/)
&nbsp;
[![License](https://img.shields.io/badge/License-MIT-yellow)](./LICENSE)

</div>

---

## 项目简介

CareerPilot 是一个面向秋招和日常求职的 AI Agent 应用。基于 LangChain 框架实现的 **ReAct（Reasoning + Acting）Agent**，集成 RAG 检索增强、多工具调用和 SQLite 业务数据管理。Agent 能根据用户意图自主判断任务类型（知识问答 / 岗位分析 / 面试准备 / 投递跟踪），调用合适的工具和知识库完成推理，并通过 Streamlit 流式界面实时展示 Agent 的思考与执行过程。


## 技术架构

<div align="center">

```text
用户输入 (Streamlit)
      │
      ▼
┌─────────────────────────────────────────┐
│            ReAct Agent                   │
│                                          │
│  ┌──────────┐    ┌──────────────────┐   │
│  │ Thought  │───→│     Action       │   │
│  │ (推理)    │    │ (工具调用 / RAG)  │   │
│  └──────────┘    └────────┬─────────┘   │
│       ↑                   │              │
│       └─── Observation ◄──┘              │
│                                          │
└─────────────────────────────────────────┘
      │                │              │
      ▼                ▼              ▼
┌──────────┐   ┌────────────┐  ┌──────────┐
│   RAG    │   │   Tools    │  │  SQLite  │
│  Chroma  │   │ 岗位/投递   │  │ 业务数据  │
│ 向量检索  │   │ 面试/资料   │  │ 持久存储  │
└──────────┘   └────────────┘  └──────────┘
```

</div>

### 核心特性

| 特性 | 说明 |
|---|---|
| **ReAct 范式** | Thought → Action → Observation 循环，Agent 自主推理并决定调用哪个工具 |
| **RAG 检索增强** | Chroma 向量库 + DashScope Embedding，MD5 文件去重，支持 txt/pdf 混合加载 |
| **多工具调用** | 候选人资料 / 岗位管理 / 匹配分析 / 面试准备 / 投递跟踪 / 知识检索，Agent 按需自动选择 |
| **SQLite 持久化** | 候选人资料、岗位、投递记录、面试安排全部存入 SQLite，重启不丢失 |
| **流式对话界面** | Streamlit 构建，支持流式逐字输出、历史消息留存、Agent 推理过程可见 |
| **模块化结构** | Agent / RAG / Model / Tools 独立模块，配置 YAML 驱动 |

## 技术栈

| 层级 | 技术 |
|---|---|
| LLM | qwen-plus（DashScope OpenAI 兼容接口，0.8 / 2 元每百万 token） |
| 视觉模型 | qwen3-vl-plus（岗位截图解析） |
| Embedding | text-embedding-v4（1024 维） |
| 模型接入 | OpenAI 兼容协议（`base_url` 可配置，换供应商只改配置） |
| Agent 框架 | LangChain + LangGraph（SqliteSaver 多轮记忆） |
| 向量数据库 | Chroma（显式 cosine 距离） |
| 业务数据库 | SQLite |
| 文档处理 | PyMuPDF（PDF 解析）+ RecursiveCharacterTextSplitter |
| 前端 | Streamlit |
| 配置 | YAML 驱动（Agent / RAG / Chroma / Prompts） |

## 快速开始

### 环境要求

- **Python** >= 3.12（开发环境 3.12.4，依赖清单按实际运行环境钉死）
- **DashScope API Key**（[阿里云百炼](https://bailian.console.aliyun.com/) 申请）

### 1. 克隆仓库

```bash
git clone <repo-url>
cd career-pilot-agent
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API Key

参考 .env.example，设置阿里云百炼 API Key：

```bash
# Linux / macOS
export DASHSCOPE_API_KEY="your-api-key"

# Windows PowerShell
$env:DASHSCOPE_API_KEY = "your-api-key"
```

或在项目根目录创建 .env 文件：

```ini
DASHSCOPE_API_KEY="your-api-key"
```

### 4. 初始化示例数据

```bash
python seed_demo_data.py
```

### 5. 启动应用

```bash
streamlit run app.py
```

## 项目结构

```text
career-pilot-agent/
├── app.py                  # Streamlit 主入口
├── career_store.py         # SQLite 数据层（7 张业务表）
├── checkpoints.db          # LangGraph 对话状态（运行后生成，多轮记忆）
├── seed_demo_data.py       # 示例数据初始化脚本
├── agent/
│   ├── react_agent.py      # ReAct Agent 核心（含 checkpointer 多轮记忆）
│   └── tools/
│       ├── agent_tools.py  # 24 个 LangChain 工具
│       └── middleware.py   # 工具调用日志
├── rag/
│   ├── rag_service.py      # RAG 检索总结服务
│   ├── vector_store.py     # 知识库向量（Chroma + MD5 去重）
│   └── match_retriever.py  # 匹配检索 + LLM 重排（cosine 距离）
├── model/
│   └── factory.py          # LLM / Embedding 模型工厂
├── config/                 # YAML 配置
├── data/career/
│   ├── knowledge/          # 求职知识库（resume/interview/job/process，10 篇约 2.3 万字）
│   └── *.txt, jobs.json    # 示例数据（不参与建库）
├── eval/                   # 检索评测（用例 + Hit@k / Recall@k / MRR 脚本）
├── prompts/                # 提示词模板
├── utils/                  # 工具函数
└── requirements.txt
```

## License

MIT
