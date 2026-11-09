# CareerPilot 求职管理 Agent（v2 版本说明）

> 本文档为 v2 历史版本，内容已过时，最新状态请见 `PROJECT_GUIDE_v4.md`。

## 1. 项目简介

CareerPilot 是一个面向秋招和日常求职的 AI Agent 应用。它使用 LangGraph 编排 ReAct Agent，结合 SQLite 业务数据和 Chroma RAG 知识库，帮助用户管理候选人资料、分析岗位、跟踪投递并准备面试。

当前版本是本地 MVP，使用 Streamlit 提供交互界面。项目内置脱敏的示例简历和 6 条示例岗位，可以直接用于演示。

相比初始版本，当前版本已新增 **岗位智能解析**（文本/截图）、**简历文件解析**（PDF/Word）和 **岗位详情展开** 等功能。

## 2. 主要功能

### 2.1 候选人资料管理

- 保存姓名、目标岗位、目标城市和技能。
- 保存结构化的简历摘要和项目经历。
- 记录资料来源（`_source` 字段）：`manual`（手动/示例）或 `resume_parse`（简历解析导入）。
- Agent 在分析岗位前可以主动读取候选人资料，避免凭空编造经历。

### 2.2 简历文件解析（新增）

支持上传 PDF 或 Word 简历文件，LLM 自动提取以下信息并更新候选人资料：

- 姓名
- 目标岗位和目标城市
- 技能列表（编程语言、框架、工具、平台等）
- 简历摘要（教育背景、核心项目、关键成果，300 字以内）

解析流程：

```text
上传文件 → 提取文本（PyMuPDF / python-docx）→ LLM 结构化提取 → 预览确认 → 保存到 SQLite
```

技术细节：
- PDF 解析使用 PyMuPDF（fitz），支持文字型 PDF。
- Word 解析使用 python-docx，同时提取段落和表格内容。
- 解析结果存入 `st.session_state`，避免 Streamlit 嵌套按钮导致保存失败。
- 保存后自动刷新页面，候选人资料立即更新。

### 2.3 岗位管理

- 保存公司、岗位名称、城市、岗位描述和来源（`manual` / `智能解析` / `截图解析`）。
- 在页面中查看岗位列表，点击卡片展开查看完整岗位描述。
- 展开卡片内提供快捷操作：分析匹配度、面试准备、加入投递。

### 2.4 岗位智能解析（新增）

支持三种岗位导入方式：

| 方式 | 说明 | 模型 |
|------|------|------|
| 手动录入 | 填写公司、岗位、城市、描述 | 无 |
| 粘贴文本智能解析 | 从招聘网站复制 JD，LLM 自动提取 | qwen3-max（文本模型） |
| 上传截图智能解析 | 上传招聘网页截图，视觉模型识别 | qwen-vl-plus（视觉模型） |

截图解析支持一次上传多张图片，批量解析并保存。

### 2.5 岗位匹配分析

Agent 会根据岗位描述和候选人资料，按以下维度分析：

- 编程与后端
- 大模型与 RAG
- 算法与数据
- 工程协作

输出内容包括：

- 0～100 的解释性匹配分数
- 已匹配技能
- 技能缺口
- 各能力维度的分项得分
- 简历证据提示
- 下一步改进建议

### 2.6 投递跟踪

支持记录和查看以下投递状态：

```text
已收藏 → 已投递 → 笔试 → 面试 → Offer
                         ↘ 拒绝 / 暂停
```

每条投递记录关联岗位、状态、备注和更新时间。投递记录是连接岗位和面试的桥梁，用于追踪求职进度、避免重复投递和遗忘。

### 2.7 面试准备

根据指定岗位生成：

- 面试准备重点
- 项目深挖问题
- 岗位技能问题
- AI 应用、RAG、Agent 和后端场景题
- 可用于回答问题的简历证据

### 2.8 求职知识库问答

通过 Chroma 保存求职知识文档，Agent 可以检索：

- 岗位匹配方法
- 简历项目表达方法
- AI 应用岗位常见技能
- 面试准备方法
- 投递状态管理建议

## 3. Agent 工作流程

```text
用户问题
   ↓
CareerPilot Agent（LangGraph create_react_agent）
   ↓
自主判断是否需要调用工具
   ├─ 读取/更新候选人资料
   ├─ 查询岗位或投递记录
   ├─ 分析岗位匹配度
   ├─ 生成面试准备内容
   ├─ 智能解析岗位文本
   ├─ 记录面试安排
   └─ 检索求职知识库（RAG）
   ↓
整理工具结果
   ↓
生成最终回答
```

项目中的 ReAct 流程是：

```text
Thought → Action → Observation → Thought → Final Answer
```

其中 Action 是工具调用，Observation 是数据库或知识库返回结果。

## 4. 项目目录

```text
career-pilot-agent/
├── agent/
│   ├── react_agent.py          # CareerPilot Agent 创建与流式执行
│   └── tools/
│       ├── agent_tools.py      # 求职资料、岗位、投递、面试、RAG、解析工具
│       └── middleware.py        # 工具中间件
├── career_store.py             # SQLite 数据库访问层（5 张表）
├── career_pilot.db             # 本地求职业务数据（运行后生成）
├── seed_demo_data.py           # 加载示例简历和岗位
├── app.py                      # Streamlit 应用入口
├── rag/
│   ├── vector_store.py         # Chroma 向量库和文档加载
│   └── rag_service.py          # RAG 检索与总结
├── model/
│   └── factory.py              # 通义千问文本/视觉/Embedding 模型工厂
├── config/
│   ├── rag.yml                 # 模型名称配置
│   ├── chroma.yml              # 向量数据库配置
│   ├── agent.yml               # Agent 配置
│   └── prompts.yml             # 提示词配置
├── prompts/
│   ├── main_prompt.txt         # Agent 系统提示词
│   ├── rag_summarize.txt       # RAG 总结提示词
│   └── report_prompt.txt       # 报告提示词
├── data/
│   ├── career/
│   │   ├── candidate_resume.txt  # 脱敏示例简历
│   │   ├── jobs.json             # 示例岗位
│   │   └── job_search_guide.txt  # 求职知识库资料
│   └── picture/                 # 用户上传的截图和简历文件
├── utils/                       # 工具函数（配置、日志、路径、提示词加载）
├── assets/                      # 界面截图
├── .env                         # API Key（不提交到版本库）
└── PROJECT_GUIDE.md             # 本说明文档
```

## 5. 环境要求

当前使用的 Python 环境：

```text
D:\anaconda\envs\pytorch_cpu
```

项目主要依赖：

| 依赖 | 用途 |
|------|------|
| Python 3.10+ | 运行环境 |
| langchain / langgraph | Agent 编排与工具调用 |
| streamlit | Web 交互界面 |
| chromadb | RAG 向量知识库 |
| sqlite3（标准库） | 业务数据持久化 |
| dashscope / ChatTongyi | 通义千问大模型 API |
| PyMuPDF（fitz） | PDF 简历文本提取 |
| python-docx | Word 简历文本提取 |

不需要 Docker，也不需要单独安装 PostgreSQL。SQLite 已经满足当前本地 MVP 的需求。

## 6. 配置 API Key

项目根目录有 `.env` 文件。请自行填写阿里云百炼的 API Key，不要把密钥发送到聊天、截图或提交记录中：

```env
DASHSCOPE_API_KEY=你的密钥
```

模型配置位于 `config/rag.yml`：

```yaml
chat_model_name: qwen3-max          # 文本模型（Agent 推理 + 文本解析）
vision_model_name: qwen-vl-plus     # 视觉模型（截图解析）
embedding_model_name: qwen3.7-text-embedding  # Embedding 模型（RAG）
```

## 7. 启动项目

### 7.1 进入项目目录

```powershell
cd C:\Users\max\Desktop\秋招\项目\career-pilot-agent
```

### 7.2 使用指定 Conda 环境启动

```powershell
D:\anaconda\envs\pytorch_cpu\python.exe -m streamlit run app.py
```

启动后访问：

```text
http://localhost:8501
```

### 7.3 重新生成示例数据库

如果希望清空本地岗位和候选人数据，可删除 `career_pilot.db` 后重新执行：

```powershell
D:\anaconda\envs\pytorch_cpu\python.exe seed_demo_data.py
```

该脚本会重新写入示例候选人和 6 条岗位。

## 8. 推荐测试问题

启动后可以在聊天框输入：

```text
读取我的求职资料，并总结我的优势和不足
```

```text
查看当前保存的岗位
```

```text
分析 ID 为 1 的岗位是否适合我
```

```text
为 ID 为 1 的岗位生成面试准备方案
```

```text
把 ID 为 1 的岗位加入投递跟踪
```

```text
查看我的投递记录
```

```text
根据 AI 应用开发岗位，帮我修改项目经历的表达
```

也可以在页面左侧"岗位与投递管理"面板中：

- 上传 PDF/Word 简历 → 点击"解析简历" → 确认保存
- 粘贴岗位 JD → 点击"智能解析并保存"
- 上传岗位截图 → 点击"解析截图并保存"
- 点击岗位卡片展开 → 快捷操作（分析/面试/投递）

## 9. 页面使用方法

### 9.1 左侧边栏

- 当前岗位数量
- 当前投递数量
- 目标岗位
- 目标城市
- 示例岗位及其 ID
- 清空聊天记录按钮

### 9.2 岗位与投递管理（展开面板）

三个标签页：

**岗位列表：**
- 表格概览（ID、公司、岗位、城市、状态、来源）
- 点击卡片展开完整岗位描述
- 展开内快捷按钮：分析匹配度 / 面试准备 / 加入投递
- 三种导入方式：手动录入 / 粘贴文本智能解析 / 上传截图智能解析

**投递记录：**
- 表格概览（ID、公司、岗位、城市、状态、备注）
- 更新投递状态表单
- 新增投递记录表单

**候选人资料：**
- 当前资料展示（姓名、目标岗位、目标城市、技能、简历摘要）
- 资料来源标识（手动/简历解析）
- 上传简历自动解析（PDF/Word）

### 9.3 聊天框

与 Agent 对话，Agent 会自主调用工具完成任务，展示思考过程和最终回答。

## 10. 数据存储说明

### 10.1 SQLite 数据库（career_pilot.db）

共 5 张表：

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| profile | 候选人资料（单行，id=1） | name, target_roles, target_cities, skills, resume_summary, _source |
| jobs | 岗位列表 | company, title, city, description, source, status |
| applications | 投递记录 | job_id → jobs(id), status, notes |
| interviews | 面试安排 | job_id → jobs(id), interview_date, stage, notes |
| chat_messages | 聊天记录 | role, content |

表关系：

```text
profile（1 行）
jobs（N 行）──1:N──→ applications（投递记录）──1:N──→ interviews（面试安排）
```

### 10.2 Chroma 向量库

RAG 向量数据存储在 Chroma 持久化目录中，用于求职知识库检索。

### 10.3 安全提醒

- 示例数据是虚构的，仅用于开发和演示。
- 真实简历使用前建议脱敏，不要把身份证号、手机号和私人地址直接放入测试数据。

## 11. 当前版本边界

这是一个可运行的本地 MVP，已经具备 Agent、RAG、SQLite 和求职业务闭环，但仍有以下限制：

- 岗位匹配评分主要依赖结构化技能词和简历证据，尚未接入更复杂的语义重排模型。
- 投递状态由用户或 Agent 工具更新，没有接入真实招聘平台。
- Streamlit 适合本地演示，尚未拆分为正式前后端服务。
- Chroma 需要正确的本地 Python/科学计算依赖环境。
- 简历解析仅支持文字型 PDF 和 Word，扫描版/图片型 PDF 需要先用截图方式上传。
- 岗位截图解析依赖视觉模型（qwen-vl-plus），识别准确率受图片质量影响。

## 12. 后续升级方向

1. ~~增加 PDF/Word 简历解析和岗位 JD 批量导入。~~（已完成：简历 PDF/Word 解析、岗位文本/截图智能解析）
2. 将岗位要求拆成学历、城市、技能、经验和加分项，支持更细粒度的匹配分析。
3. 使用向量检索和重排模型生成更可靠的匹配证据，替代当前的关键词匹配方式。
4. 增加简历版本管理和针对岗位的定制简历导出，支持同一用户维护多版简历。
5. 增加面试记录、复盘和求职任务提醒，形成完整的求职闭环。
6. 增加评测集，统计匹配准确率、工具调用成功率和回答引用质量。
7. 后续再升级 FastAPI、PostgreSQL 和 Docker Compose，从本地 MVP 过渡到可部署服务。