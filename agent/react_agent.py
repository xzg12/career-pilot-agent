from dotenv import load_dotenv
load_dotenv()

import sqlite3
from dataclasses import replace
from pathlib import Path

# LangGraph 1.0 起 create_react_agent 已标记弃用，官方入口迁移到 langchain.agents
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, trim_messages
from langchain_core.messages.utils import count_tokens_approximately

from model.factory import chat_model
from utils.prompt_loader import load_system_prompts
from utils.logger_handler import logger
from utils.path_tool import get_abs_path
from agent.tools.agent_tools import (analyze_job_match,generate_interview_prep,get_application_tracker,get_candidate_profile,get_jobs,parse_and_save_job,save_job,schedule_interview,get_interview_records,review_interview,add_task_reminder,get_task_list,update_task_status,sync_candidate_vector,sync_job_vector,create_resume_version,list_resume_versions,get_current_resume,switch_resume_version,export_resume_for_job,search_career_knowledge,track_application,update_application_status,update_candidate_profile)

# 短期记忆（多轮对话）持久化文件，和业务库 career_pilot.db 分开存
CHECKPOINT_DB = get_abs_path("checkpoints.db")
DEFAULT_THREAD_ID = "default"

# 每次调模型时允许携带的历史 token 预算。
# checkpointer 只负责「存」，不负责「省」，历史会无限增长，必须在调模型前裁剪。
MAX_CONTEXT_TOKENS = 6000


def _open_checkpointer():
    conn = sqlite3.connect(CHECKPOINT_DB, check_same_thread=False)
    return conn, SqliteSaver(conn)


class TrimHistoryMiddleware(AgentMiddleware):
    """调模型前裁剪历史，只影响本次输入，不改 checkpointer 里保存的完整 state。

    替代旧版的 pre_model_hook：create_agent 把「调模型前介入」统一收敛到 middleware，
    wrap_model_call 拿到的 ModelRequest 可以替换 messages 后继续调用，语义等价。
    """

    def wrap_model_call(self, request, handler):
        messages = request.messages
        if not messages:
            return handler(request)

        try:
            trimmed = trim_messages(
                messages,
                max_tokens=MAX_CONTEXT_TOKENS,
                token_counter=count_tokens_approximately,
                strategy="last",        # 保留最近的消息
                start_on="human",       # 保证以用户消息开头，避免出现孤立的 ToolMessage
                allow_partial=False,    # 不拆分消息，保证 tool_call 与 tool_result 成对
            )
        except Exception as e:
            logger.warning(f"[记忆裁剪]失败，回退到最近 10 条：{e}")
            trimmed = messages[-10:]

        if not trimmed:
            # 边界情况：单条消息本身就超出预算时，trim_messages 会返回空列表，
            # 模型会拿不到当前问题。这里从最后一次提问开始兜底保留，宁可超预算也不能空。
            human_idx = max(
                (i for i, m in enumerate(messages) if isinstance(m, HumanMessage)),
                default=len(messages) - 1,
            )
            trimmed = messages[human_idx:]
            logger.warning(f"[记忆裁剪]预算 {MAX_CONTEXT_TOKENS} 不足以容纳单条消息，回退保留最近一次提问起的 {len(trimmed)} 条")

        if len(trimmed) < len(messages):
            logger.info(f"[记忆裁剪]{len(messages)} 条 -> {len(trimmed)} 条（预算 {MAX_CONTEXT_TOKENS} tokens）")
        return handler(replace(request, messages=trimmed))


class CareerPilotAgent:
    def __init__(self, thread_id: str = DEFAULT_THREAD_ID):
        self.thread_id = thread_id

        Path(CHECKPOINT_DB).parent.mkdir(parents=True, exist_ok=True)
        # Streamlit 每次交互可能在不同线程执行，关闭同线程校验，避免 sqlite3 报错
        self._conn, self.checkpointer = _open_checkpointer()

        self.agent = create_agent(
            model=chat_model,
            tools=[search_career_knowledge, get_candidate_profile, update_candidate_profile, save_job, parse_and_save_job, get_jobs, analyze_job_match, generate_interview_prep, track_application, get_application_tracker, update_application_status, schedule_interview, get_interview_records, review_interview, add_task_reminder, get_task_list, update_task_status, sync_candidate_vector, sync_job_vector, create_resume_version, list_resume_versions, get_current_resume, switch_resume_version, export_resume_for_job],
            system_prompt=load_system_prompts(),
            checkpointer=self.checkpointer,
            middleware=[TrimHistoryMiddleware()],
        )

    @property
    def config(self):
        return {"configurable": {"thread_id": self.thread_id}}

    def execute_stream(self, query: str):
        # 只传当前这一句，历史由 checkpointer 按 thread_id 自动恢复
        seen = set()   # stream_mode='values' 会在同一 super-step 内重复发快照，按消息 id 去重
        for chunk in self.agent.stream(
            {'messages': [{'role': 'user', 'content': query}]},
            config=self.config,
            stream_mode='values',
        ):
            latest = chunk['messages'][-1]
            msg_id = getattr(latest, 'id', None)
            if msg_id is not None:
                if msg_id in seen:
                    continue
                seen.add(msg_id)
            if not latest.content: continue
            if isinstance(latest, ToolMessage): yield 'tool', latest.content.strip()+'\n'
            elif isinstance(latest, AIMessage) and latest.tool_calls: yield 'thinking', (latest.content or '正在选择工具…').strip()+'\n'
            elif isinstance(latest, AIMessage): yield 'answer', latest.content.strip()+'\n'

    def clear_memory(self) -> bool:
        """清空当前会话的记忆（checkpointer 里的 thread）"""
        return clear_thread_memory(self.thread_id)


def clear_thread_memory(thread_id: str = DEFAULT_THREAD_ID) -> bool:
    """独立函数：页面上的「清空聊天记录」直接调用，不依赖 agent 实例"""
    try:
        conn, saver = _open_checkpointer()
        saver.delete_thread(thread_id)
        conn.close()
        logger.info(f"[记忆]已清空 thread：{thread_id}")
        return True
    except Exception as e:
        logger.warning(f"[记忆]清空 thread 失败：{e}")
        return False


ReactAgent = CareerPilotAgent
