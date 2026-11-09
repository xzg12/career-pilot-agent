from dotenv import load_dotenv
load_dotenv()

import os
import time
import streamlit as st
from agent.react_agent import CareerPilotAgent
from career_store import (get_profile, list_jobs, list_applications, init_db,
                          add_application, update_application, add_job,
                          update_profile,
                          save_message, load_messages, clear_messages,
                          list_interviews, get_interview, update_interview,
                          add_task, list_tasks, update_task,
                          add_resume, list_resumes, get_resume, get_active_resume, update_resume, set_active_resume, delete_resume)

init_db()

st.set_page_config(page_title="CareerPilot 求职管理 Agent", page_icon="🎯")
st.title("🎯 CareerPilot 求职管理 Agent")
st.caption("基于 LangChain + ReAct + RAG 的求职管理助手")
st.divider()


@st.cache_resource(show_spinner=False)
def _bootstrap_knowledge_base():
    """启动时加载一次求职知识库；文件没变时靠 MD5 去重，不会重复调用 Embedding 接口"""
    from rag.vector_store import ensure_knowledge_loaded
    return ensure_knowledge_loaded()


with st.spinner("正在初始化求职知识库…"):
    kb_status = _bootstrap_knowledge_base()


profile = get_profile()
jobs = list_jobs()
applications = list_applications()
with st.sidebar:
    st.subheader("求职概览")
    st.metric("岗位数量", len(jobs))
    st.metric("投递数量", len(applications))
    st.caption(f"目标：{profile.get('target_roles') or '尚未设置'}")
    st.caption(f"城市：{profile.get('target_cities') or '尚未设置'}")
    st.divider()
    st.subheader("知识库")
    kb_state = kb_status.get("status")
    if kb_state == "error":
        st.warning(f"知识库加载失败：{str(kb_status.get('error', '未知错误'))[:90]}")
        st.caption("RAG 检索将返回空结果，请检查 Embedding 额度后点击下方按钮重试")
    elif kb_state == "empty":
        st.info("data/career 下没有可加载的 txt/pdf 文档")
    else:
        kb_line = f"文件 {kb_status.get('loaded', 0)} 个 · 片段 {kb_status.get('chunks', 0)} 个"
        if kb_status.get("skipped"):
            kb_line += f" · 跳过 {kb_status['skipped']} 个"
        st.caption(kb_line)
    if st.button("🔄 重建全部向量", use_container_width=True):
        with st.spinner("正在重建全部向量（知识库 + 候选人 + 岗位）…"):
            from rag.vector_store import ensure_knowledge_loaded
            from rag.rag_service import reset_rag_service
            from rag.match_retriever import (reset_match_collections, sync_candidate_to_vector,
                                             sync_job_to_vector)
            try:
                result = ensure_knowledge_loaded(force=True)
                reset_match_collections()
                sync_candidate_to_vector()
                sync_job_to_vector()
                reset_rag_service()
                _bootstrap_knowledge_base.clear()
            except Exception as e:
                result = {"status": "error", "error": str(e)[:300]}
        st.session_state["kb_notice"] = result
        st.rerun()

    kb_notice = st.session_state.pop("kb_notice", None)
    if kb_notice:
        if kb_notice.get("status") == "error":
            st.error(f"重建失败：{str(kb_notice.get('error', ''))[:90]}")
        else:
            st.success(f"已重建：知识库 {kb_notice.get('loaded', 0)} 个文件 / "
                       f"{kb_notice.get('chunks', 0)} 个片段，候选人+岗位向量已重新同步")
    st.divider()
    st.subheader("示例岗位")
    for job in jobs[:6]:
        st.write(f"{job['id']} {job['company']} · {job['title']}")
    st.divider()
    if st.button("🗑️ 清空聊天记录"):
        # chat_messages 只负责页面回显，真正喂给模型的历史在 checkpointer 里，两边必须一起清
        from agent.react_agent import clear_thread_memory
        clear_thread_memory()
        clear_messages()
        st.session_state.pop("agent", None)
        st.rerun()

with st.expander("岗位与投递管理", expanded=False):
    tab_jobs, tab_apps, tab_interviews, tab_tasks, tab_resumes, tab_profile = st.tabs(["岗位列表", "投递记录", "面试记录", "任务提醒", "简历版本", "候选人资料"])
    with tab_jobs:
        if jobs:
            st.dataframe([{k: j[k] for k in ('id','company','title','city','status','source')} for j in jobs], use_container_width=True, hide_index=True)
            st.caption("点击下方卡片展开查看完整岗位描述")
            for job in jobs:
                with st.expander(f"📋 {job['id']}: {job['company']} - {job['title']} ({job.get('city', '')})", expanded=False):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**公司：** {job['company']}")
                        st.write(f"**岗位：** {job['title']}")
                    with col_b:
                        st.write(f"**城市：** {job.get('city', '未填写')}")
                        st.write(f"**状态：** {job['status']}")
                        st.write(f"**来源：** {job.get('source', '手动录入')}")
                    st.divider()
                    st.subheader("岗位描述")
                    st.markdown(job.get('description', '暂无描述'))
                    c1, c2, c3 = st.columns(3)
                    if c1.button("🔍 分析匹配度", key=f"match_{job['id']}", use_container_width=True):
                        st.session_state[f'chat_input_{job["id"]}'] = f"分析 ID 为 {job['id']} 的岗位是否适合我"
                    if c2.button("📝 面试准备", key=f"prep_{job['id']}", use_container_width=True):
                        st.session_state[f'chat_input_{job["id"]}'] = f"为 ID 为 {job['id']} 的岗位生成面试准备"
                    if c3.button("🎯 加入投递", key=f"track_{job['id']}", use_container_width=True):
                        from career_store import add_application
                        add_application(job['id'], "已收藏")
                        st.success(f"已将 {job['company']} - {job['title']} 加入投递跟踪")
        st.divider()
        import_mode = st.radio("导入方式", ["📝 手动录入", "🧠 粘贴文本智能解析", "📸 上传截图智能解析"], horizontal=True, key="import_mode")
        if import_mode == "📝 手动录入":
            with st.form("new_job_form", clear_on_submit=True):
                company = st.text_input("公司")
                title = st.text_input("岗位名称")
                city = st.text_input("城市")
                description = st.text_area("岗位描述")
                submitted = st.form_submit_button("保存岗位")
                if submitted and company and title and description:
                    add_job(company, title, description, city)
                    st.success("岗位已保存，刷新页面后可在 Agent 中分析")
        elif import_mode == "🧠 粘贴文本智能解析":
            st.caption("从招聘网站复制岗位描述粘贴到下方，LLM 自动提取公司、岗位、城市和描述")
            raw_jd = st.text_area("粘贴岗位描述", height=200, key="raw_jd_input", placeholder="例如：\n字节跳动 | AI应用开发工程师 | 北京\n岗位职责：...\n任职要求：...")
            if st.button("🔍 智能解析并保存", key="parse_jd_btn") and raw_jd.strip():
                with st.spinner("LLM 正在解析岗位信息..."):
                    from agent.tools.agent_tools import parse_job_text
                    result = parse_job_text(raw_jd.strip())
                if result.get("parse_ok"):
                    st.success(f"解析成功！**{result['company']}** - **{result['title']}** ({result.get('city', '')})")
                    add_job(result["company"], result["title"], result["description"], result.get("city", ""), source="智能解析")
                    st.info("岗位已保存，刷新页面后可在列表和 Agent 中查看")
                else:
                    st.error("解析失败，LLM 输出格式异常，请尝试手动录入")
                    if result.get("error"):
                        with st.expander("查看 LLM 原始输出"):
                            st.code(result["error"])
        elif import_mode == "📸 上传截图智能解析":
            st.caption("上传招聘网页截图，视觉模型自动识别岗位信息并保存（支持一次上传多张）")
            uploaded_files = st.file_uploader("上传岗位截图", type=["png", "jpg", "jpeg", "webp", "bmp"], accept_multiple_files=True, key="jd_image_uploader")
            if uploaded_files and st.button("🔍 解析截图并保存", key="parse_image_btn"):
                from agent.tools.agent_tools import parse_job_image
                results = []
                for i, uploaded_file in enumerate(uploaded_files):
                    with st.spinner(f"正在解析第 {i+1}/{len(uploaded_files)} 张截图..."):
                        image_bytes = uploaded_file.read()
                        result = parse_job_image(image_bytes)
                        results.append((uploaded_file.name, result))
                st.divider()
                success_count = 0
                for fname, result in results:
                    if result.get("parse_ok"):
                        success_count += 1
                        st.success(f"✅ {fname}：**{result['company']}** - **{result['title']}** ({result.get('city', '')})")
                        add_job(result["company"], result["title"], result["description"], result.get("city", ""), source="截图解析")
                    else:
                        st.error(f"❌ {fname}：解析失败")
                        if result.get("error"):
                            with st.expander(f"查看 {fname} 的 LLM 输出"):
                                st.code(result["error"])
                if success_count > 0:
                    st.info(f"成功保存 {success_count} 个岗位，刷新页面后可在列表和 Agent 中查看")
    with tab_apps:
        apps = list_applications()
        if apps:
            st.dataframe([{k: a[k] for k in ('id','company','title','city','status','notes')} for a in apps], use_container_width=True, hide_index=True)
            st.divider()
            with st.form("update_app_form", clear_on_submit=True):
                st.write("更新投递状态")
                app_id = st.number_input("投递记录 ID", min_value=1, step=1)
                new_status = st.selectbox("状态", ["已收藏", "已投递", "笔试", "面试", "Offer", "拒绝", "暂停"])
                new_notes = st.text_input("备注（可选）")
                update_submitted = st.form_submit_button("更新状态")
                if update_submitted:
                    res = update_application(int(app_id), status=new_status, notes=new_notes if new_notes else None)
                    if res:
                        st.success(f"投递记录 {app_id} 已更新为 {new_status}")
                    else:
                        st.error(f"未找到投递记录 {app_id}")
        else:
            st.info("还没有投递记录，可以通过下方表单或对话添加。")
        st.divider()
        with st.form("new_app_form", clear_on_submit=True):
            st.write("新增投递记录")
            job_options = {f"{j['id']}: {j['company']} - {j['title']}": j['id'] for j in jobs} if jobs else {}
            selected_job = st.selectbox("选择岗位", list(job_options.keys())) if job_options else st.text_input("岗位 ID（暂无岗位，请先添加岗位）")
            app_status = st.selectbox("投递状态", ["已收藏", "已投递", "笔试", "面试", "Offer", "拒绝", "暂停"], index=0)
            app_notes = st.text_input("备注（可选）")
            app_submitted = st.form_submit_button("保存投递记录")
            if app_submitted and job_options:
                jid = job_options[selected_job]
                add_application(jid, app_status, app_notes)
                st.success(f"已将岗位 {jid} 加入投递跟踪，状态：{app_status}")
            elif app_submitted and not job_options:
                st.error("暂无岗位，请先在岗位列表中添加岗位")
    with tab_interviews:
        interviews = list_interviews()
        if interviews:
            st.dataframe([{k: iv[k] for k in ('id','company','title','stage','round_num','interview_date')} for iv in interviews], use_container_width=True, hide_index=True)
            st.caption("点击下方卡片展开查看面试详情和复盘")
            for iv in interviews:
                with st.expander(f"🎤 {iv['id']}: {iv['company']} - {iv['title']} 第{iv.get('round_num',1)}轮 ({iv.get('stage', '待安排')})", expanded=False):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**公司：** {iv['company']}")
                        st.write(f"**岗位：** {iv['title']}")
                        st.write(f"**轮次：** 第{iv.get('round_num', 1)}轮")
                    with c2:
                        st.write(f"**状态：** {iv.get('stage', '待安排')}")
                        st.write(f"**日期：** {iv.get('interview_date', '未定')}")
                    if iv.get('questions'):
                        st.subheader("面试问题")
                        st.write(iv['questions'])
                    if iv.get('self_eval'):
                        st.subheader("自我评价")
                        st.write(iv['self_eval'])
                    if iv.get('review'):
                        st.subheader("复盘分析")
                        try:
                            import json
                            review_data = json.loads(iv['review'])
                            if isinstance(review_data, dict):
                                if review_data.get('overall_score'):
                                    st.metric("整体评分", f"{review_data['overall_score']}/10")
                                if review_data.get('summary'):
                                    st.info(f"💡 {review_data['summary']}")
                                if review_data.get('strengths'):
                                    st.subheader("✅ 表现好的方面")
                                    for s in review_data['strengths']:
                                        st.write(f"- {s}")
                                if review_data.get('weaknesses'):
                                    st.subheader("⚠️ 需要改进")
                                    for w in review_data['weaknesses']:
                                        st.write(f"- {w}")
                                if review_data.get('improvement_actions'):
                                    st.subheader("🎯 改进行动")
                                    for a in review_data['improvement_actions']:
                                        st.write(f"- {a}")
                                if review_data.get('next_prep_focus'):
                                    st.subheader("📋 下次准备重点")
                                    for f_item in review_data['next_prep_focus']:
                                        st.write(f"- {f_item}")
                            else:
                                st.write(iv['review'])
                        except (json.JSONDecodeError, TypeError):
                            st.write(iv['review'])
                    if iv.get('notes'):
                        st.subheader("备注")
                        st.write(iv['notes'])
                    st.divider()
                    if st.button(f"🔄 AI 复盘分析", key=f"review_iv_{iv['id']}"):
                        with st.spinner("LLM 正在分析面试表现..."):
                            from agent.tools.agent_tools import review_interview
                            result = review_interview.invoke({"interview_id": iv['id']})
                        st.success("复盘完成，刷新页面查看结果")
                        st.rerun()
        else:
            st.info('还没有面试记录，可以在岗位列表中点击"面试准备"或在聊天框让 Agent 记录面试。')
        st.divider()
        with st.form("new_interview_form", clear_on_submit=True):
            st.write("新增面试记录")
            iv_job_options = {f"{j['id']}: {j['company']} - {j['title']}": j['id'] for j in jobs} if jobs else {}
            iv_selected_job = st.selectbox("选择岗位", list(iv_job_options.keys())) if iv_job_options else st.text_input("岗位 ID")
            iv_round = st.number_input("面试轮次", min_value=1, value=1, step=1)
            iv_stage = st.selectbox("面试状态", ["待安排", "已通过", "未通过", "待结果"], index=0)
            iv_date = st.text_input("面试日期（如 2026-09-15）")
            iv_questions = st.text_area("面试问题（每行一个）", height=100)
            iv_self_eval = st.text_area("自我评价（回答得怎么样）", height=100)
            iv_notes = st.text_input("备注（可选）")
            iv_submitted = st.form_submit_button("保存面试记录")
            if iv_submitted and iv_job_options:
                from career_store import add_interview
                add_interview(iv_job_options[iv_selected_job], interview_date=iv_date, stage=iv_stage, round_num=iv_round, questions=iv_questions, self_eval=iv_self_eval, notes=iv_notes)
                st.success("面试记录已保存")

    with tab_tasks:
        task_filter = st.radio("筛选", ["待完成", "已完成", "全部"], horizontal=True, key="task_filter")
        task_status = "" if task_filter == "全部" else task_filter
        tasks = list_tasks(task_status)
        if tasks:
            for t in tasks:
                due = t.get('due_date', '')
                is_overdue = False
                if due and t.get('status') == '待完成':
                    try:
                        from datetime import datetime
                        is_overdue = datetime.now().strftime("%Y-%m-%d") > due
                    except Exception:
                        pass
                icon = "🔴" if is_overdue else ("✅" if t.get('status') == '已完成' else "🟡")
                with st.container(border=True):
                    tc1, tc2, tc3 = st.columns([5, 2, 2])
                    with tc1:
                        st.write(f"{icon} **{t.get('description', '')}**")
                        st.caption(f"{t.get('company', '')} - {t.get('title', '')} | 类型：{t.get('task_type', '待办')}")
                    with tc2:
                        st.write(f"截止：{due or '无'}")
                    with tc3:
                        if t.get('status') == '待完成':
                            if st.button("✅ 完成", key=f"done_task_{t['id']}"):
                                update_task(t['id'], status='已完成')
                                st.rerun()
        else:
            st.info("没有任务提醒，可以在聊天框让 Agent 添加任务，或手动新增。")
        st.divider()
        with st.form("new_task_form", clear_on_submit=True):
            st.write("新增任务")
            t_job_options = {f"{j['id']}: {j['company']} - {j['title']}": j['id'] for j in jobs} if jobs else {}
            t_selected_job = st.selectbox("关联岗位", list(t_job_options.keys())) if t_job_options else st.text_input("岗位 ID")
            t_type = st.selectbox("任务类型", ["待办", "笔试准备", "面试准备", "跟进HR", "提交材料", "其他"])
            t_desc = st.text_input("任务描述")
            t_due = st.text_input("截止日期（如 2026-09-15）")
            t_submitted = st.form_submit_button("保存任务")
            if t_submitted and t_job_options and t_desc:
                add_task(t_job_options[t_selected_job], task_type=t_type, description=t_desc, due_date=t_due)
                st.success("任务已保存")

    with tab_resumes:
        resumes = list_resumes()
        active = get_active_resume()
        export_job_options = {f"{j['id']}: {j['company']} - {j['title']}": j['id'] for j in jobs} if jobs else {}
        export_job_label = st.selectbox(
            "导出简历时面向的岗位（用于推荐最合适的版本）",
            list(export_job_options.keys()),
            key="export_job_selector",
        ) if export_job_options else None
        if active:
            st.success(f"当前激活：{active['version_name']}（目标类型：{active.get('target_type', '通用')}）")
        else:
            st.info("还没有激活的简历版本，请创建或激活一个")
        st.divider()
        if resumes:
            for r in resumes:
                is_active = r.get('is_active', 0) == 1
                icon = "🟢" if is_active else "⚪"
                with st.expander(f"{icon} {r['id']}: {r['version_name']}（{r.get('target_type', '通用')}）", expanded=False):
                    rc1, rc2 = st.columns(2)
                    with rc1:
                        st.write(f"**版本名称：** {r['version_name']}")
                        st.write(f"**目标类型：** {r.get('target_type', '通用')}")
                    with rc2:
                        st.write(f"**状态：** {'激活' if is_active else '未激活'}")
                        st.write(f"**创建时间：** {r.get('created_at', '')}")
                    if r.get('skills'):
                        st.subheader("技能")
                        st.write(r['skills'])
                    if r.get('resume_summary'):
                        st.subheader("简历摘要")
                        st.write(r['resume_summary'][:500])
                    if r.get('projects'):
                        st.subheader("项目经历")
                        st.write(r['projects'][:500])
                    if r.get('education'):
                        st.subheader("教育背景")
                        st.write(r['education'])
                    st.divider()
                    bc1, bc2, bc3 = st.columns(3)
                    if not is_active and bc1.button("激活此版本", key=f"activate_r_{r['id']}"):
                        set_active_resume(r['id'])
                        st.rerun()
                    if bc2.button("删除", key=f"del_r_{r['id']}"):
                        delete_resume(r['id'])
                        st.rerun()
                    if bc3.button("导出 Word", key=f"export_r_{r['id']}"):
                        with st.spinner("正在导出..."):
                            from agent.tools.agent_tools import _export_resume_impl
                            if export_job_label:
                                result = _export_resume_impl(export_job_options[export_job_label])
                                import json
                                try:
                                    data = json.loads(result)
                                    if data.get('file'):
                                        st.success(f"已导出到：{data['file']}")
                                    else:
                                        st.error(data.get('error', '导出失败'))
                                except json.JSONDecodeError:
                                    st.error("导出失败")
                            else:
                                st.warning("没有岗位，无法导出")
        else:
            st.info("还没有简历版本，可以在下方创建，或从当前候选人资料快速创建")
        st.divider()
        with st.form("new_resume_form", clear_on_submit=True):
            st.write("新建简历版本")
            nr_name = st.text_input("版本名称（如：算法方向版、应用开发版）")
            nr_type = st.selectbox("目标类型", ["通用", "算法", "应用开发", "后端开发", "前端开发", "数据分析", "其他"])
            nr_skills = st.text_area("技能（逗号分隔）", height=80)
            nr_summary = st.text_area("简历摘要", height=100)
            nr_projects = st.text_area("项目经历（每行一个）", height=100)
            nr_edu = st.text_area("教育背景（每行一个）", height=60)
            nr_submitted = st.form_submit_button("创建简历版本")
            if nr_submitted and nr_name:
                new_r = add_resume(nr_name, target_type=nr_type, skills=nr_skills, resume_summary=nr_summary, projects=nr_projects, education=nr_edu)
                st.success(f"简历版本 '{nr_name}' 已创建（ID={new_r['id']}）")
        st.divider()
        if st.button("从当前候选人资料快速创建简历版本", key="quick_resume"):
            profile = get_profile()
            if profile and profile.get('skills'):
                quick_name = f"通用版_{profile.get('name', '默认')}"
                add_resume(quick_name, target_type='通用', skills=profile.get('skills', ''), resume_summary=profile.get('resume_summary', ''))
                st.success(f"已从候选人资料创建简历版本：{quick_name}")
                st.rerun()
            else:
                st.warning("候选人资料为空，请先填写")

    with tab_profile:
        st.subheader("当前候选人资料")
        if profile.get("_source") == "resume_parse":
            st.info("📄 此资料由简历自动解析导入（可手动编辑下方表单覆盖）")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**姓名：** {profile.get('name')}")
            st.write(f"**目标岗位：** {profile.get('target_roles') or '未设置'}")
        with col2:
            st.write(f"**目标城市：** {profile.get('target_cities') or '未设置'}")
            st.write(f"**技能：** {profile.get('skills') or '未设置'}")
        with st.expander("简历摘要"):
            st.write(profile.get('resume_summary') or '未设置')
        st.divider()
        st.subheader("📄 上传简历自动解析")
        st.caption("上传 PDF 或 Word 简历文件，LLM 自动提取姓名、技能、项目经历并更新候选人资料")
        resume_file = st.file_uploader("上传简历文件", type=["pdf", "docx", "doc"], key="resume_uploader")
        if resume_file and st.button("🔍 解析简历", key="parse_resume_btn"):
            with st.spinner("正在读取简历文件并调用 LLM 解析..."):
                from agent.tools.agent_tools import parse_resume_file
                file_bytes = resume_file.read()
                result = parse_resume_file(file_bytes, resume_file.name)
            if result.get("parse_ok"):
                st.session_state["resume_parse_result"] = result
                st.success(f"✅ 解析成功！提取到 **{result.get('name', '未知')}** 的简历信息")
            else:
                st.error(f"❌ 解析失败：{result.get('error', '未知错误')}")
                st.info("提示：如果是扫描版 PDF（图片型），文字无法提取，请尝试截图后用\"上传截图智能解析\"功能")
        if "resume_parse_result" in st.session_state:
            result = st.session_state["resume_parse_result"]
            with st.container(border=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**姓名：** {result.get('name', '')}")
                    st.write(f"**目标岗位：** {result.get('target_roles', '')}")
                    st.write(f"**目标城市：** {result.get('target_cities', '')}")
                with col_b:
                    st.write(f"**技能：** {result.get('skills', '')}")
                with st.expander("简历摘要"):
                    st.write(result.get('resume_summary', ''))
            if st.button("💾 确认并保存到数据库", key="confirm_resume_btn"):
                update_profile(
                    name=result.get('name', ''),
                    target_roles=result.get('target_roles', ''),
                    target_cities=result.get('target_cities', ''),
                    skills=result.get('skills', ''),
                    resume_summary=result.get('resume_summary', '')
                )
                import sqlite3
                db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "career_pilot.db")
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("UPDATE profile SET _source='resume_parse' WHERE id=1")
                conn.commit()
                conn.close()
                del st.session_state["resume_parse_result"]
                st.success("✅ 候选人资料已保存到 SQLite 数据库 (career_pilot.db)")
                st.balloons()
                st.rerun()

if "agent" not in st.session_state:
    st.session_state["agent"] = CareerPilotAgent()

messages = load_messages()

for message in messages:
    st.chat_message(message["role"]).write(message["content"])

prompt = st.chat_input()

if prompt:
    st.chat_message("user").write(prompt)
    save_message("user", prompt)

    thinking_content = []
    answer_content = []

    with st.status("🤔 思考中...", expanded=True) as status:
        res_stream = st.session_state["agent"].execute_stream(prompt)

        for msg_type, chunk in res_stream:
            if msg_type in ("thinking", "tool"):
                thinking_content.append(chunk)
                st.write(chunk)
            elif msg_type == "answer":
                answer_content.append(chunk)

        if thinking_content:
            status.update(label="✅ 思考完成", expanded=False)

    if answer_content:
        answer_text = "".join(answer_content)

        def stream_generator(text):
            for char in text:
                time.sleep(0.01)
                yield char

        st.chat_message("assistant").write_stream(stream_generator(answer_text))
        save_message("assistant", answer_text)
    elif thinking_content and not answer_content:
        full_response = "".join(thinking_content)
        st.chat_message("assistant").write(full_response)
        save_message("assistant", full_response)
