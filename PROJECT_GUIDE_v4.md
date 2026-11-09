# CareerPilot 求职管理 Agent（v4 版本说明）

> 本文档基于 PROJECT_GUIDE_v3 更新，反映升级 4（简历版本管理）完成后的完整项目状态，并详细说明升级 6（评测集）的设计方案与未实现原因。

---

## 1. 项目简介

CareerPilot 是一个基于 LangGraph ReAct Agent 的求职管理助手，帮助秋招和长期求职者完成以下闭环：

```text
简历版本管理 → 岗位收集与智能解析 → 结构化匹配分析 → 投递跟踪 → 面试准备 → 面试记录与复盘 → 任务提醒
```

当前版本在 MVP 基础上已完成四项核心升级：

- **升级 2**：岗位要求拆解（学历/城市/技能/经验/加分项），支持更细粒度的匹配分析
- **升级 3**：向量检索 + LLM 重排模型生成更可靠的匹配证据
- **升级 4**：简历版本管理，支持多版本简历创建、切换、针对岗位导出 Word 文档
- **升级 5**：面试记录、AI 复盘和求职任务提醒，形成完整求职闭环

## 2. 主要功能

### 2.1 候选人资料管理

- 读取和更新候选人资料（姓名、目标岗位、目标城市、技能、简历摘要）
- 支持 PDF/Word 简历文件解析，自动提取技能和摘要
- 资料来源标识（手动录入 / 简历解析）
- 候选人资料可同步到向量库用于语义匹配检索（Agent 工具 `sync_candidate_vector`，或侧边栏「重建全部向量」）

### 2.2 简历文件解析

- 支持 PDF 简历（PyMuPDF 提取文字）
- 支持 Word 简历（python-docx 提取文字）
- LLM 自动解析为结构化 JSON（姓名、技能、项目经历、教育背景等）
- 解析结果预览 → 确认保存到数据库

### 2.3 简历版本管理（升级 4）

- 创建多个简历版本，每个版本可指定：
  - 版本名称（如"后端开发版"、"AI应用版"）
  - 目标岗位类型（如"后端"、"AI/算法"、"通用"）
  - 技能列表、简历摘要、项目经历、教育背景
- 激活/切换当前使用的简历版本
- 查看所有简历版本列表，支持删除
- 针对岗位智能推荐最合适的简历版本
- 一键导出简历为 Word 文档（.docx），文件名包含版本名和目标岗位
- 导出的 Word 文档包含：联系方式、技能、摘要、项目经历、教育背景等结构化段落

### 2.4 岗位管理

- 手动录入岗位信息
- 粘贴岗位 JD 文本 → LLM 智能解析并保存
- 上传岗位官网截图 → 视觉模型识别 → LLM 解析并保存
- 岗位列表卡片展开查看完整描述
- 展开内快捷按钮：分析匹配度 / 面试准备 / 加入投递
- 岗位描述可同步到向量库（Agent 工具 `sync_job_vector`，或侧边栏「重建全部向量」）

### 2.5 岗位智能解析

- 从岗位 JD 自动提取：公司、岗位名称、城市、描述、来源
- 截图解析使用视觉模型（qwen3-vl-plus）识别图片内容
- 文本解析使用 LLM 提取结构化信息

### 2.6 结构化岗位匹配分析（升级 2）

- LLM 自动拆解岗位要求为 6 个维度：
  - 学历要求（硬性/优先）
  - 工作城市
  - 必须技能
  - 加分技能
  - 经验要求
  - 其他条件（必须/加分）
- 逐项与候选人资料匹配，加权打分
- 技能别名映射（如 "LLM" ↔ "大模型"、"RAG" ↔ "检索增强生成"）
- 输出分项得分、匹配技能、缺口技能、针对性建议

### 2.7 向量检索 + 重排匹配证据（升级 3）

- 候选人资料和岗位描述分别向量化存入独立 Chroma collection
- 匹配分析时自动检索语义相近的证据
- LLM 重排模型对检索结果按相关性打分和排序
- 与结构化拆解互补：精确匹配 + 语义匹配双证据

### 2.8 投递跟踪

- 将岗位加入投递跟踪，记录投递状态（已收藏 → 已投递 → 笔试 → 面试 → Offer / 拒绝 / 暂停）
- 查看所有投递记录，更新状态和备注
- 投递记录是连接岗位和面试的桥梁

### 2.9 面试记录与 AI 复盘（升级 5）

- 记录面试详情：轮次、面试问题、自我评价、备注
- AI 复盘分析：LLM 根据面试记录生成整体评分、优势、薄弱环节、改进行动、下次准备重点
- 复盘结果持久化保存，可随时查看
- 面试记录列表卡片展开查看完整详情

### 2.10 求职任务提醒（升级 5）

- 添加求职任务：笔试准备、面试准备、跟进 HR、提交材料等
- 设置截止日期，逾期任务标红提醒
- 按状态筛选（待完成/已完成/全部）
- 一键标记任务完成

### 2.11 面试准备

- 先拆解岗位 JD（必须/加分技能、学历、经验），再结合候选人资料生成方案
- 输出总体策略、准备重点、8–10 道分类问题（技术深挖 / 项目追问 / 场景设计 / 行为面试，每题含考察点与回答要点）和能力缺口
- 问题会落到候选人自己的项目经历上，并对缺失技能专门出题

### 2.12 求职知识库检索（RAG）

- 基于向量知识库的求职、简历、面试知识检索
- 使用 Chroma + DashScope Embedding

### 2.13 多轮对话记忆

- 基于 LangGraph checkpointer（SqliteSaver）持久化会话状态，存于 `checkpoints.db`
- 用 `thread_id` 区分会话，每次只传当前这一句，历史由框架自动恢复
- 调模型前用自定义 middleware（`TrimHistoryMiddleware`，挂在 `wrap_model_call` 上）+ `trim_messages` 按 6000 token 预算裁剪，不影响已保存的完整历史
- 侧边栏「清空聊天记录」会同时清空 `chat_messages` 和 checkpointer 中的 thread

### 2.14 检索效果评测

`eval/` 目录提供可重复的检索度量，避免「改了参数只能靠感觉判断」。

- `eval/cases.json`：23 条用例（4 个主题 + 5 条口语化难例），每条标注期望命中的文档
- `eval/run_eval.py`：输出 Hit@k、Recall@k、MRR 三个指标
- 支持 `--k` 调节召回数量、`--rerank` 对比重排前后、`--json` 保存明细做前后对比

当前基线（10 篇 / 85 片段）：纯向量 k=3 时 **Hit@3 = 100%、MRR = 0.978**。

检索重排已在 `rag/reranker.py` 实现，但**默认关闭**——评测显示当前语料规模下重排与纯向量指标持平（k=1 时都是 95.7%），却要多一次 LLM 调用。配置 `rerank_enabled: true` 可随时开启。

## 3. Agent 工作流程

```text
用户提问
   ↓
LangGraph（create_agent）
   ↓
ReAct 循环（Thought → Action → Observation）
   ↓
选择工具：
   ├─ 候选人资料工具（读取/更新）
   ├─ 岗位工具（保存/查询/智能解析/截图解析）
   ├─ 匹配分析工具（结构化拆解 + 向量检索重排）
   ├─ 投递工具（加入跟踪/查看/更新状态）
   ├─ 面试工具（安排/查看记录/AI 复盘）
   ├─ 任务工具（添加/查看/更新状态）
   ├─ 简历版本工具（创建/列表/查看/切换/导出）
   ├─ 向量同步工具（候选人/岗位同步到向量库）
   └─ 知识库检索工具（RAG）
   ↓
整理工具结果
   ↓
生成最终回答
```

## 4. 项目目录

```text
career-pilot-agent/
├── agent/
│   ├── react_agent.py          # CareerPilot Agent 创建与流式执行
│   └── tools/
│       ├── agent_tools.py      # 求职资料、岗位、投递、面试、任务、匹配、RAG、解析、简历版本工具
│       └── middleware.py        # 工具中间件
├── career_store.py             # SQLite 数据库访问层（7 张表）
├── career_pilot.db             # 本地求职业务数据（运行后生成）
├── seed_demo_data.py           # 加载示例简历和岗位
├── app.py                      # Streamlit 应用入口
├── rag/
│   ├── vector_store.py         # Chroma 向量库和文档加载（知识库）
│   ├── rag_service.py          # RAG 检索与总结
│   └── match_retriever.py      # 匹配专用向量检索 + LLM 重排（升级 3）
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
├── PROJECT_GUIDE.md             # 原始说明文档
├── PROJECT_GUIDE_v2.md          # v2 说明文档
├── PROJECT_GUIDE_v3.md          # v3 说明文档
└── PROJECT_GUIDE_v4.md          # 本文档
```

## 5. 环境要求

当前使用的 Python 环境：

```text
D:\anaconda\envs\pytorch_cpu
```

项目主要依赖：

| 依赖 | 用途 |
|------|------|
| Python 3.12+ | 运行环境（开发环境 3.12.4） |
| langgraph 1.2 / langchain-core 1.6 / langchain-openai 1.6 | Agent 编排与工具调用（OpenAI 兼容接口） |
| streamlit 1.62 | Web 交互界面 |
| chromadb 1.5 / langchain-chroma 1.1 | RAG 向量知识库 + 匹配向量检索 |
| sqlite3（标准库） | 业务数据持久化 |
| 阿里云百炼（OpenAI 兼容接口） | 通义千问大模型 API |
| PyMuPDF / python-docx | PDF 解析 / 简历导出 |
| PyMuPDF（fitz） | PDF 简历文本提取 |
| python-docx | Word 简历文本提取与导出 |

不需要 Docker，也不需要单独安装 PostgreSQL。SQLite 已经满足当前本地 MVP 的需求。

## 6. 配置 API Key

项目根目录有 `.env` 文件。请自行填写阿里云百炼的 API Key，不要把密钥发送到聊天、截图或提交记录中：

```env
DASHSCOPE_API_KEY=你的密钥
```

模型配置位于 `config/rag.yml`：

```yaml
chat_model_name: qwen-plus          # 文本模型（Agent 推理 + 文本解析 + 重排），0.8 / 2 元每百万 token
vision_model_name: qwen3-vl-plus    # 视觉模型（截图解析）
embedding_model_name: text-embedding-v4  # Embedding 模型（RAG + 匹配向量）
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

### 7.4 向量库初始化

应用启动时会自动把 `data/career/knowledge/` 下的 txt/md/pdf 加载进知识库，靠文件 MD5 去重，文件没变就不会重复调用 Embedding。目录按主题分四类（resume / interview / job / process），共 9 篇约 2 万字，切分后 75 个片段；示例数据（简历、jobs.json）放在 `data/career/` 根目录，不参与建库。

候选人和岗位的匹配向量需要额外同步，两种方式：

1. 侧边栏 → 点击「重建全部向量」（一次性重建知识库 + 候选人 + 岗位）
2. 或在聊天框让 Agent 执行：`同步我的资料到向量库`

> 注意：更换 Embedding 模型后必须重建向量库，否则新旧向量不在同一空间，检索结果会失真。

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
同步我的资料到向量库
```

```text
记录面试：岗位 ID 为 1，一面问了自我介绍和项目深挖，我项目讲得还行但算法有点卡
```

```text
复盘一下面试记录 ID 为 1 的面试
```

```text
帮我添加一个任务：准备字节跳动笔试，截止 9 月 14 日
```

```text
查看我的待办任务
```

```text
创建一个简历版本，名称叫"后端开发版"，目标类型是后端，技能是Python,FastAPI,Docker,MySQL
```

```text
查看所有简历版本
```

```text
为岗位 ID 为 1 导出最合适的简历
```

也可以在页面左侧"岗位与投递管理"面板中：

- 上传 PDF/Word 简历 → 点击"解析简历" → 确认保存
- 粘贴岗位 JD → 点击"智能解析并保存"
- 上传岗位截图 → 点击"解析截图并保存"
- 点击岗位卡片展开 → 快捷操作（分析/面试/投递）
- 面试记录标签页 → 新增面试记录 → AI 复盘分析
- 任务提醒标签页 → 新增任务 → 标记完成
- 简历版本标签页 → 创建/切换/导出简历版本
- 侧边栏 → 重建全部向量

## 9. 页面使用方法

### 9.1 左侧边栏

- 当前岗位数量
- 当前投递数量
- 目标岗位
- 目标城市
- 示例岗位及其 ID
- 清空聊天记录按钮

### 9.2 岗位与投递管理（展开面板）

六个标签页：

**岗位列表：**
- 表格概览（ID、公司、岗位、城市、状态、来源）
- 点击卡片展开完整岗位描述
- 展开内快捷按钮：分析匹配度 / 面试准备 / 加入投递
- 三种导入方式：手动录入 / 粘贴文本智能解析 / 上传截图智能解析

**投递记录：**
- 表格概览（ID、公司、岗位、城市、状态、备注）
- 更新投递状态表单
- 新增投递记录表单

**面试记录（升级 5）：**
- 表格概览（ID、公司、岗位、轮次、状态、日期）
- 点击卡片展开查看完整详情：
  - 面试问题、自我评价
  - AI 复盘分析（整体评分、优势、薄弱环节、改进行动、下次准备重点）
  - 备注
  - "AI 复盘分析"按钮（一键触发 LLM 复盘）
- 新增面试记录表单（选择岗位、轮次、状态、日期、问题、自我评价、备注）

**任务提醒（升级 5）：**
- 按状态筛选（待完成/已完成/全部）
- 任务卡片展示：描述、关联岗位、类型、截止日期
- 逾期任务标红提醒，待完成标黄，已完成标绿
- 一键标记完成
- 新增任务表单（关联岗位、类型、描述、截止日期）

**简历版本（升级 4）：**
- 当前激活版本提示（版本名 + 目标类型）
- 简历版本列表卡片：
  - 版本名称、目标类型、技能摘要
  - 激活状态标识（已激活 / 未激活）
  - 操作按钮：激活此版本 / 删除 / 导出 Word
- 创建新简历版本表单：
  - 版本名称（必填）
  - 目标岗位类型（默认"通用"）
  - 技能列表、简历摘要、项目经历、教育背景
- 针对岗位导出简历：
  - 顶部下拉框选择目标岗位 → 自动推荐最匹配的简历版本
  - 一键导出为 Word 文档（.docx）
  - 导出文件保存到 `data/picture/` 目录

**候选人资料：**
- 当前资料展示（姓名、目标岗位、目标城市、技能、简历摘要）
- 资料来源标识（手动/简历解析）
- 上传简历自动解析（PDF/Word）
- 向量同步：侧边栏「重建全部向量」，或通过 Agent 工具 `sync_candidate_vector` / `sync_job_vector`

### 9.3 聊天框

与 Agent 对话，Agent 会自主调用工具完成任务，展示思考过程和最终回答。

## 10. 数据存储说明

### 10.1 SQLite 数据库（career_pilot.db）

共 7 张表：

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| profile | 候选人资料（单行，id=1） | name, target_roles, target_cities, skills, resume_summary, _source |
| jobs | 岗位列表 | company, title, city, description, source, status |
| applications | 投递记录 | job_id → jobs(id), status, notes |
| interviews | 面试记录 | job_id → jobs(id), interview_date, stage, round_num, questions, self_eval, review, notes |
| tasks | 求职任务 | job_id → jobs(id), task_type, description, due_date, status |
| resumes | 简历版本 | version_name, target_type, skills, resume_summary, projects, education, is_active |
| chat_messages | 聊天记录 | role, content |

表关系：

```text
profile（1 行）
jobs（N 行）──1:N──→ applications（投递记录）
              ──1:N──→ interviews（面试记录：轮次/问题/评价/复盘）
              ──1:N──→ tasks（求职任务：类型/描述/截止日期/状态）
resumes（N 行，is_active 标记当前激活版本）
```

另外还有独立的 `checkpoints.db`（LangGraph 对话状态快照），和业务库分开存放：业务数据要长期保留，对话状态可以随时丢弃重建。侧边栏「清空聊天记录」会同时清空 `chat_messages` 和这个文件里的 thread。

### 10.2 Chroma 向量库

共 3 个 collection：

| collection | 用途 | 数据来源 |
|------------|------|----------|
| career_pilot | RAG 求职知识库 | data/career/knowledge/ 下的 txt/md/pdf 文件 |
| candidate_profile | 候选人资料向量 | 技能、简历摘要、目标岗位 |
| job_jd | 岗位描述向量 | 各岗位的 JD 描述 |

三个 collection 都显式配置了 `hnsw:space = cosine`（Chromadb 默认是 L2 平方距离，分数无上界且无法换算成相似度）。余弦距离值域 [0,2]，代码里用 `1 - distance` 截断到 [0,1] 作为相似度。

> space 在 collection 创建时写死，改配置对已有 collection 无效，必须删库重建。更换 Embedding 模型同理。

### 10.3 安全提醒

- 示例数据是虚构的，仅用于开发和演示。
- 真实简历使用前建议脱敏，不要把身份证号、手机号和私人地址直接放入测试数据。

## 11. 当前版本边界

这是一个可运行的本地 MVP，已经具备 Agent、RAG、SQLite、结构化匹配、向量检索重排、简历版本管理和求职业务闭环，但仍有以下限制：

- 候选人和岗位的匹配向量需要手动同步，新增或修改后要重建，否则匹配证据会过期。
- LLM 重排增加一次额外 API 调用，匹配分析延迟约 2-3 秒。
- 投递状态由用户或 Agent 工具更新，没有接入真实招聘平台。
- Streamlit 适合本地演示，尚未拆分为正式前后端服务。
- Chroma 需要正确的本地 Python/科学计算依赖环境。
- 简历解析仅支持文字型 PDF 和 Word，扫描版/图片型 PDF 需要先用截图方式上传。
- 岗位截图解析依赖视觉模型（qwen3-vl-plus），识别准确率受图片质量影响。
- 面试复盘依赖面试问题和自我评价的记录质量，记录越详细复盘越有价值。
- 任务提醒是静态的，没有推送通知功能（需要页面刷新才能看到更新）。
- 简历版本导出为 Word 文档，暂不支持 PDF 格式导出。
- 简历版本推荐由 LLM 从版本列表中挑选（`_export_resume_impl`），选错时需要人工改选。
- 尚未实现评测集，无法量化 Agent 的匹配准确率、工具调用成功率和回答引用质量。

## 12. 后续升级方向

1. ~~增加 PDF/Word 简历解析和岗位 JD 批量导入。~~（已完成：简历 PDF/Word 解析、岗位文本/截图智能解析）
2. ~~将岗位要求拆成学历、城市、技能、经验和加分项，支持更细粒度的匹配分析。~~（已完成：LLM 拆解 + 逐项加权匹配 + 技能别名）
3. ~~使用向量检索和重排模型生成更可靠的匹配证据。~~（已完成：双 Chroma collection + LLM 重排，与结构化拆解互补）
4. ~~增加简历版本管理和针对岗位的定制简历导出，支持同一用户维护多版简历。~~（已完成：多版本 CRUD + 激活切换 + 岗位推荐导出 Word）
5. ~~增加面试记录、复盘和求职任务提醒。~~（已完成：面试详情记录 + AI 复盘 + 任务提醒 + 逾期标红）
6. 增加评测集，统计匹配准确率、工具调用成功率和回答引用质量。（设计方案见第 13 节，当前未实现）
7. 后续再升级 FastAPI、PostgreSQL 和 Docker Compose，从本地 MVP 过渡到可部署服务。

---

## 13. 升级 6 详细设计：评测集方案说明

> 本节详细说明升级 6（评测集）的设计方案、三个评测指标的含义与计算方法、实现架构、未实现原因，以及业界相关框架。虽未实现，但方案已完整设计，可作为后续开发参考，也可用于面试中展示对 Agent 质量保障的系统性理解。

### 13.1 什么是评测集

评测集（Evaluation Dataset / Benchmark）是一组"标准问答对"，每条包含一个**输入**和一个**期望输出（Ground Truth / 标注答案）**，用来量化衡量 Agent 回答的"正确性"和"质量"。

**类比**：就像考试有"标准答案"，评测集就是 Agent 的"考试卷 + 标准答案"。跑完自动和标准答案对比，就知道"考了多少分"。

**在本项目中的具体数据格式**：

```json
[
  {
    "id": "E001",
    "category": "岗位匹配",
    "query": "分析岗位1的匹配度",
    "expected_tools": ["analyze_job_match"],
    "expected_score_range": [60, 80],
    "expected_matched_skills": ["Python", "LangChain"],
    "expected_missing_skills": ["Kubernetes"],
    "reference_keywords": ["匹配", "技能", "建议"]
  },
  {
    "id": "E002",
    "category": "面试准备",
    "query": "帮我准备岗位2的面试",
    "expected_tools": ["generate_interview_prep"],
    "reference_keywords": ["面试题", "技术点", "项目经历"]
  },
  {
    "id": "E003",
    "category": "任务提醒",
    "query": "提醒我明天提交简历",
    "expected_tools": ["add_task_reminder"],
    "reference_keywords": ["任务", "提醒"]
  }
]
```

### 13.2 三个评测指标详解

#### 13.2.1 匹配准确率（Match Accuracy）

**定义**：Agent 给出的岗位匹配分析结果，和人工标注的"标准匹配结论"一致的比例。

**在本项目中**，`analyze_job_match` 会输出总分、各维度得分、匹配/缺失技能列表、建议文本。评测就是看这些输出和"标准答案"差多少：

```text
评测方法：
- 分数偏差：|Agent 输出分数 - 标注分数| < 阈值（如 10 分）→ 算正确
- 技能匹配精确率 = |Agent 匹配技能 ∩ 标注匹配技能| / |Agent 匹配技能|
- 技能匹配召回率 = |Agent 匹配技能 ∩ 标注匹配技能| / |标注匹配技能|
- 缺失技能召回率 = |Agent 缺失技能 ∩ 标注缺失技能| / |标注缺失技能|

举例：
  标注答案：匹配技能 = [Python, LangChain, FastAPI]，缺失技能 = [K8s, Go]
  Agent 输出：匹配技能 = [Python, LangChain, Docker]，缺失技能 = [K8s, Go]

  技能匹配精确率 = 2/3 = 66.7%（Python 和 LangChain 命中，FastAPI 漏了）
  技能匹配召回率 = 2/3 = 66.7%
  缺失召回率 = 2/2 = 100%（K8s 和 Go 都找出来了）
```

**面试话术**："匹配准确率衡量的是 Agent 对岗位 JD 的拆解和候选人技能的比对是否准确。具体来说，我会构造一组标注了标准匹配结果的测试用例，然后让 Agent 对同一组岗位运行匹配分析，比较输出分数偏差、技能匹配/缺失的召回率和精确率。"

#### 13.2.2 工具调用成功率（Tool Call Success Rate）

**定义**：Agent 在处理用户请求时，**正确选择并成功调用**所需工具的比例。

拆分为两个子指标：

- **工具选择准确率**：Agent 是否选对了工具（该调 `analyze_job_match` 时有没有调对）
- **工具执行成功率**：调对了工具后，工具是否成功执行并返回有效结果（没报错、没返回空值）

```text
评测方法：
- 对每条评测用例，记录 Agent 实际调用的工具链
- 和 expected_tools 对比

举例：
  用户问："帮我分析第 3 个岗位的匹配度"
  期望工具调用：analyze_job_match(job_id=3)
  实际工具调用：get_jobs() → analyze_job_match(job_id=3)  ✅ 选对了

  用户问："帮我预约明天下午的面试"
  期望工具调用：schedule_interview(...)
  实际工具调用：get_interview_records()  ❌ 选错了

  工具选择准确率 = 正确选择次数 / 总测试次数
  工具执行成功率 = 成功执行次数 / 总调用次数
```

**面试话术**："工具调用成功率衡量的是 ReAct Agent 的工具选择和执行能力。我通过构造不同类型的用户请求，标注每个请求应该调用的工具序列，然后运行 Agent 对比实际调用链。这能发现 Agent 是否'选错工具'或'调用参数不对'等问题。"

#### 13.2.3 回答引用质量（Answer Citation Quality / Faithfulness）

**定义**：Agent 的最终回答是否**有据可依**，即回答内容是否来自检索到的真实数据，而不是 LLM 编造的（幻觉）。

三个子维度：

- **忠实性（Faithfulness）**：回答中的每个论断是否都能在检索证据中找到出处
- **相关性（Relevance）**：回答是否紧扣用户问题，没有跑题
- **完整性（Completeness）**：回答是否覆盖了问题的关键方面

```text
评测方法：
- 对每条评测用例，收集 Agent 的中间检索结果（向量检索返回的文档片段）
- 用另一个 LLM（或人工）判断：回答中的每个论断是否能在检索结果中找到依据

举例：
  用户问："我匹配这个岗位的优势是什么？"
  检索证据：候选人技能 = [Python, LangChain, RAG]，岗位必须技能 = [Python, LangChain, Docker]
  Agent 回答："你的优势是 Python 和 LangChain 技能完全匹配，但 Docker 需要补充"

  评判：Python 匹配 → 证据中有 ✅，LangChain 匹配 → 证据中有 ✅，Docker 缺失 → 证据中有 ✅
  忠实性 = 3/3 = 100%

  如果 Agent 回答："你的优势是 Java 和 Spring Boot"（幻觉）
  评判：Java → 证据中没有 ❌，Spring Boot → 证据中没有 ❌
  忠实性 = 0/2 = 0%
```

**面试话术**："回答引用质量衡量的是 Agent 是否产生了幻觉。我通过收集 Agent 检索到的中间证据，然后逐条验证回答中的论断是否能在证据中找到出处。这和 RAG 系统的 Faithfulness 评测是同一思路，参考了 RAGAS 框架的 faithfulness 指标。"

### 13.3 实现架构

```text
新增目录结构：
career-pilot-agent/
├── eval/                          # 评测模块
│   ├── eval_dataset.json          # 评测集（标准问答对）
│   ├── run_eval.py                # 评测运行脚本
│   ├── metrics.py                 # 指标计算（匹配准确率、工具成功率、引用质量）
│   └── eval_report.html           # 评测报告（自动生成）
```

**核心评测流程**：

```text
加载评测集（eval_dataset.json）
   ↓
逐条运行 Agent，记录中间过程（trace）
   ├─ 实际调用的工具链
   ├─ 工具返回结果
   └─ 检索到的文档片段
   ↓
计算三个指标：
   ├─ 匹配准确率 = f(Agent 匹配输出, 标注答案)
   ├─ 工具调用成功率 = f(实际工具链, 期望工具链)
   └─ 回答引用质量 = f(最终回答, 检索证据)
   ↓
汇总生成评测报告
```

**核心代码伪实现**：

```python
import json
from agent.react_agent import CareerPilotAgent

def run_evaluation():
    agent = CareerPilotAgent()
    dataset = json.load(open("eval/eval_dataset.json"))
    results = []

    for case in dataset:
        # 运行 Agent，记录中间过程（需改造 Agent 加 trace 功能）
        response, tool_calls, retrieved_docs = agent.invoke_with_trace(case["query"])

        # 计算三个指标
        match_acc = calc_match_accuracy(response, case)
        tool_success = calc_tool_success(tool_calls, case["expected_tools"])
        citation_quality = calc_citation_quality(response, retrieved_docs)

        results.append({
            "id": case["id"],
            "match_accuracy": match_acc,
            "tool_success_rate": tool_success,
            "citation_quality": citation_quality
        })

    # 汇总报告
    report = {
        "total": len(results),
        "avg_match_accuracy": mean([r["match_accuracy"] for r in results]),
        "avg_tool_success_rate": mean([r["tool_success_rate"] for r in results]),
        "avg_citation_quality": mean([r["citation_quality"] for r in results])
    }
    return report
```

### 13.4 未实现原因

| 原因 | 详细说明 |
|------|----------|
| **标注成本高** | 每条评测数据都需要人工标注 Ground Truth（标准匹配分数、标准技能列表等），需要业务专家逐条审核。当前岗位数据量不大，标注几十条数据的统计意义有限 |
| **Agent 输出不确定性** | LLM 每次输出可能不同，同一问题跑两次结果可能不一样，需要多次运行取平均才能得到稳定指标 |
| **需改造 Agent 框架** | 当前 CareerPilotAgent 只返回最终回答，评测需要拿到中间过程（调了哪些工具、检索了哪些文档），需要加 trace 功能 |
| **引用质量评测本身需要 LLM** | 判断"回答是否基于证据"需要另一个 LLM 来评判（LLM-as-Judge），引入新的不确定性 |
| **项目阶段优先级** | MVP 阶段，用户可直接在界面上看到匹配结果并人工判断，比构造评测集更直接。等核心功能稳定后再做评测才有意义 |
| **同等时间投入 ROI 更低** | 实现面试复盘、简历版本管理等功能用户直接可感知，评测集是质量保障层面，优先级更低 |

**面试回答建议**：

> "评测集这一步我没有实现，主要是基于投入产出比和项目阶段的考虑：第一，标注成本太高，当前数据量有限，标注几十条的统计意义不大；第二，MVP 阶段更适合人工验证，用户可以直接在界面上看到匹配结果；第三，Agent 输出有不确定性，模型和 prompt 还在频繁调整，评测集维护成本高；第四，同等时间投入，用户直接感知的功能优先。如果后续要做，我会参考 RAGAS 框架的 faithfulness 指标，用 LangSmith 追踪工具调用链，先小规模标注 20-30 条核心场景跑通流程。"

### 13.5 业界相关框架

| 框架 | 说明 | 与本项目的关系 |
|------|------|---------------|
| **RAGAS** | 专门评测 RAG 系统的开源框架，提供 Faithfulness、Answer Relevancy、Context Recall 等指标 | 回答引用质量可直接用 RAGAS 的 faithfulness 指标 |
| **LangSmith** | LangChain 官方的评测和可观测性平台，可追踪 Agent 每步工具调用，自动计算成功率 | 工具调用成功率可用 LangSmith 的 trace 功能实现 |
| **DeepEval** | 开源 LLM 评测框架，提供 Faithfulness、Hallucination、Tool Correctness 等指标 | 三个指标均可使用 DeepEval 实现 |
| **PromptFoo** | 提示词评测工具，可批量跑评测用例对比不同 prompt 的效果 | 优化 prompt 时可用 PromptFoo 做 A/B 对比 |

**关键概念补充**：

- **Ground Truth**："真实标签"或"标准答案"。在评测集中，每条测试用例的期望输出就是 Ground Truth。Agent 的输出和 Ground Truth 对比，才能算出准确率。
- **LLM-as-Judge**：因为很多评测维度（如回答质量、忠实性）没有客观标准答案，所以用另一个强大的 LLM（如 GPT-4）来当"裁判"，对被评测 LLM 的输出打分。优点是可扩展、成本低；缺点是裁判本身也有不确定性。
- **回归测试**：评测集最核心的价值。每次改 prompt 或匹配逻辑，跑一下评测集就能立刻知道是变好了还是变差了，避免"改了 A 坏了 B"的问题。

### 13.6 如果现在实现，具体步骤

1. **构造评测数据**：标注 20-30 条核心场景（岗位匹配、面试准备、任务提醒、简历版本各覆盖 5-8 条）
2. **改造 Agent 加 trace**：在 CareerPilotAgent 的 invoke 方法中增加中间过程记录，返回工具调用链和检索结果
3. **实现指标计算**：编写 metrics.py，实现三个指标的计算函数
4. **运行评测出报告**：编写 run_eval.py，批量运行评测用例，汇总生成 HTML 报告
5. **根据结果优化**：根据评测报告定位问题，优化 prompt、工具描述或匹配逻辑
6. **持续回归**：每次改动后重新跑评测集，确保不退化
