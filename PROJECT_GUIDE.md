duqu# CareerPilot 求职管理 Agent

> 本文档为 v1 历史版本，内容已过时，最新状态请见 `PROJECT_GUIDE_v4.md`。

## 1. 项目简介

CareerPilot 是一个面向秋招和日常求职的 AI Agent 应用。它使用 LangChain/LangGraph 编排 ReAct Agent，结合 SQLite 业务数据和 Chroma RAG 知识库，帮助用户管理候选人资料、分析岗位、跟踪投递并准备面试。

当前版本是本地 MVP，使用 Streamlit 提供交互界面。项目内置脱敏的示例简历和 6 条示例岗位，可以直接用于演示。

## 2. 主要功能

### 2.1 候选人资料管理

- 保存姓名、目标岗位、目标城市和技能。
- 保存结构化的简历摘要和项目经历。
- Agent 在分析岗位前可以主动读取候选人资料，避免凭空编造经历。

### 2.2 岗位管理

- 保存公司、岗位名称、城市、岗位描述和来源。
- 在页面中查看岗位列表。
- 支持通过对话让 Agent 查询岗位。
- 支持手动新增岗位。

### 2.3 岗位匹配分析

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

### 2.4 投递跟踪

支持记录和查看以下投递状态：

```text
已收藏 → 已投递 → 笔试 → 面试 → Offer
                         ↘ 拒绝 / 暂停
```

每条投递记录关联岗位、状态、备注和更新时间。

### 2.5 面试准备

根据指定岗位生成：

- 面试准备重点
- 项目深挖问题
- 岗位技能问题
- AI 应用、RAG、Agent 和后端场景题
- 可用于回答问题的简历证据

### 2.6 求职知识库问答

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
CareerPilot Agent
   ↓
自主判断是否需要调用工具
   ├─ 读取候选人资料
   ├─ 查询岗位或投递记录
   ├─ 分析岗位匹配度
   ├─ 生成面试准备内容
   └─ 检索求职知识库
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
│   └── tools/agent_tools.py    # 求职资料、岗位、投递、面试和 RAG 工具
├── career_store.py             # SQLite 数据库访问层
├── career_pilot.db             # 本地求职业务数据（运行后生成）
├── seed_demo_data.py           # 加载示例简历和岗位
├── app.py                      # Streamlit 应用入口
├── rag/
│   ├── vector_store.py         # Chroma 向量库和文档加载
│   └── rag_service.py          # RAG 检索与总结
├── model/factory.py            # 通义千问和 Embedding 模型配置
├── config/                     # YAML 配置
├── prompts/                    # Agent 和 RAG 提示词
├── data/career/
│   ├── candidate_resume.txt    # 脱敏示例简历
│   ├── jobs.json               # 示例岗位
│   └── job_search_guide.txt    # 求职知识库资料
└── PROJECT_GUIDE.md            # 本说明文档
```

## 5. 环境要求

当前使用的 Python 环境：

```text
D:\anaconda\envs\pytorch_cpu
```

项目主要依赖：

- Python 3.10+
- LangChain
- LangGraph
- Streamlit
- Chroma
- SQLite
- DashScope / 通义千问

不需要 Docker，也不需要单独安装 PostgreSQL。SQLite 已经满足当前本地 MVP 的需求。

## 6. 配置 API Key

项目根目录有 `.env` 文件。请自行填写阿里云百炼的 API Key，不要把密钥发送到聊天、截图或提交记录中：

```env
DASHSCOPE_API_KEY=你的密钥
```

模型和 Embedding 名称位于：

```text
config/rag.yml
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

## 9. 页面使用方法

左侧边栏会显示：

- 当前岗位数量
- 当前投递数量
- 目标岗位
- 目标城市
- 示例岗位及其 ID

展开“岗位与投递管理”后可以：

- 查看岗位列表
- 手动新增岗位
- 查看投递记录
- 查看候选人资料

## 10. 数据存储说明

- 候选人资料、岗位、投递和面试安排存储在 `career_pilot.db`。
- RAG 向量数据存储在 Chroma 持久化目录中。
- 示例数据是虚构的，仅用于开发和演示。
- 真实简历使用前建议脱敏，不要把身份证号、手机号和私人地址直接放入测试数据。

## 11. 当前版本边界

这是一个可运行的本地 MVP，已经具备 Agent、RAG、SQLite 和求职业务闭环，但仍有以下限制：

- 岗位匹配评分主要依赖结构化技能词和简历证据，尚未接入更复杂的语义重排模型。
- 岗位来源目前是手动录入或示例数据，没有自动抓取招聘网站。
- 投递状态由用户或 Agent 工具更新，没有接入真实招聘平台。
- Streamlit 适合本地演示，尚未拆分为正式前后端服务。
- Chroma 需要正确的本地 Python/科学计算依赖环境。

## 12. 后续升级方向

1. 增加 PDF/Word 简历解析和岗位 JD 批量导入。
2. 将岗位要求拆成学历、城市、技能、经验和加分项。
3. 使用向量检索和重排模型生成更可靠的匹配证据。
4. 增加简历版本管理和针对岗位的定制简历导出。
5. 增加面试记录、复盘和求职任务提醒。
6. 增加评测集，统计匹配准确率、工具调用成功率和回答引用质量。
7. 后续再升级 FastAPI、PostgreSQL 和 Docker Compose。
