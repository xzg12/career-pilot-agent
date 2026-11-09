from dotenv import load_dotenv
load_dotenv()

from langchain_core.tools import tool
from utils.logger_handler import logger
from career_store import add_application, add_interview, add_job, get_job, get_profile, list_applications, list_jobs, serialize, update_application, update_profile, list_interviews, get_interview, update_interview, add_task, list_tasks, update_task, add_resume, list_resumes, get_resume, get_active_resume, update_resume, set_active_resume, delete_resume
from rag.match_retriever import sync_candidate_to_vector, sync_job_to_vector, vector_match_evidence, rerank_with_llm

PARSE_JOB_PROMPT = """你是一个岗位信息提取助手。用户会提供一段岗位描述（可能是文本或从图片中识别的内容），请从中提取以下字段，以 JSON 格式返回：

{
  "company": "公司名称",
  "title": "岗位名称",
  "city": "工作城市（多个用、分隔，提取不到则为空字符串）",
  "description": "清洗后的完整岗位描述（保留原始要求，去掉广告和无关内容，用换行符分段）"
}

要求：
1. 严格从内容中提取，不要编造没有的信息
2. company 和 title 是必填，提取不到时设为 "未知"
3. 只输出 JSON，不要输出任何其他内容
4. 确保 JSON 格式合法
"""

PARSE_JOB_TEXT_PROMPT = PARSE_JOB_PROMPT + """

待解析的岗位描述：
{raw_text}
"""

PARSE_JOB_IMAGE_PROMPT = PARSE_JOB_PROMPT + """

请从以上图片中识别并提取岗位信息。
"""

PARSE_RESUME_PROMPT = """你是一个简历信息提取助手。用户会提供一份简历的文本内容，请从中提取以下字段，以 JSON 格式返回：

{{
  "name": "姓名",
  "target_roles": "目标岗位（如"AI应用开发工程师, Python后端工程师"，多个用逗号分隔，提取不到则为空字符串）",
  "target_cities": "目标城市（多个用逗号分隔，提取不到则为空字符串）",
  "skills": "技能列表（从简历中提取所有技术技能，用逗号分隔，如"Python, FastAPI, LangChain, RAG, Docker"）",
  "resume_summary": "简历摘要（包含教育背景、核心项目经历、关键成果，300字以内，突出与目标岗位相关的内容）"
}}

要求：
1. 严格从简历文本中提取，不要编造没有的信息
2. name 是必填，提取不到时设为 "未知"
3. skills 要尽可能全面，包括编程语言、框架、工具、平台等
4. resume_summary 要精炼，突出技术能力和项目成果，不要简单复述原文
5. 只输出 JSON，不要输出任何其他内容
6. 确保 JSON 格式合法

待解析的简历内容：
{resume_text}
"""

INTERVIEW_REVIEW_PROMPT = """你是一个面试复盘助手。根据面试记录和候选人资料，生成详细的复盘分析。

面试信息：
- 公司：{company}
- 岗位：{title}
- 面试轮次：第{round_num}轮
- 面试问题：{questions}
- 自我评价：{self_eval}

候选人资料：
- 技能：{skills}
- 简历摘要：{resume_summary}

请从以下角度进行复盘分析，以 JSON 格式返回：

{{
  "overall_score": "整体表现评分（1-10）",
  "strengths": ["表现好的方面1", "表现好的方面2"],
  "weaknesses": ["需要改进的方面1", "需要改进的方面2"],
  "key_insights": ["关键洞察1", "关键洞察2"],
  "improvement_actions": ["具体改进行动1", "具体改进行动2"],
  "next_prep_focus": ["下次面试准备重点1", "下次面试准备重点2"],
  "summary": "一句话总结本次面试表现"
}}

要求：
1. 严格根据面试记录分析，不要编造
2. improvement_actions 要具体可执行
3. next_prep_focus 要针对薄弱环节
4. 只输出 JSON，不要输出其他内容
5. 确保 JSON 格式合法
"""

INTERVIEW_PREP_PROMPT = """你是一位资深的 {job_category} 方向面试官。请根据目标岗位和候选人资料，生成一份可直接使用的面试准备方案。

## 岗位信息
- 公司 / 岗位：{company} - {title}
- 岗位类别：{job_category}
- 必须技能：{must_skills}
- 加分技能：{nice_skills}
- 学历 / 经验要求：{education} / {experience}
- 岗位描述（节选）：{jd_text}

## 候选人资料
- 技能：{skills}
- 简历摘要：{resume_summary}

## 输出要求
以 JSON 返回：

{{
  "focus": ["准备重点1", "准备重点2", "准备重点3"],
  "questions": [
    {{"type": "技术深挖", "question": "问题正文", "why": "考察点", "answer_hint": "回答要点，2-3 句"}},
    {{"type": "场景设计", "question": "问题正文", "why": "考察点", "answer_hint": "回答要点，2-3 句"}}
  ],
  "gaps": ["候选人明显缺失或薄弱的点"],
  "strategy": "一句话总体策略"
}}

## 约束
1. focus 给 3-5 条，必须同时结合该岗位的具体要求和候选人的现状，不要写通用套话
2. questions 给 8-10 条，覆盖四类：技术深挖、项目追问、场景设计、行为面试
3. 至少一半的问题要能落到候选人自己的项目经历上，而不是泛泛而谈
4. 候选人缺失的必须技能，要专门出题帮他提前准备
5. answer_hint 要具体到技术点和量化结果，不要空话
6. 只输出 JSON，不要输出任何解释
"""

PARSE_JD_STRUCTURED_PROMPT = """你是一个岗位要求拆解助手。请将以下岗位描述拆解为结构化字段，以 JSON 格式返回：

{{
  "education": "学历要求（如"硕士优先"、"本科及以上"、"不限"，提取不到则为"未明确"）",
  "education_required": true或false（是否为硬性要求，"优先"为false，"必须/及以上"为true）,
  "cities": ["工作城市1", "工作城市2"],
  "experience_years": "经验要求（如"应届可"、"1-3年"、"3年以上"，提取不到则为"未明确"）",
  "experience_required": true或false（是否为硬性要求）,
  "must_have_skills": ["必须掌握的技能1", "必须掌握的技能2"],
  "nice_to_have_skills": ["加分项技能1", "加分项技能2"],
  "must_have_qualifications": ["其他必须条件1（如特定证书、特定背景）"],
  "nice_to_have_qualifications": ["其他加分条件1"],
  "job_category": "岗位类别（如AI应用开发、后端开发、算法、前端、数据等）",
  "summary": "一句话概括该岗位核心要求"
}}

要求：
1. 严格从岗位描述中提取，不要编造
2. must_have_skills 是 JD 中明确要求"必须/必须掌握/必须具备"的技能
3. nice_to_have_skills 是 JD 中"优先/加分/熟悉/了解/具有"的技能
4. 技能要具体，如"Python"而不是"编程语言"
5. 只输出 JSON，不要输出其他内容
6. 确保 JSON 格式合法

待拆解的岗位描述：
{jd_text}
"""

@tool(description='检索求职、简历、面试和岗位技能知识库')
def search_career_knowledge(query: str) -> str:
    from rag.rag_service import get_rag_service
    return get_rag_service().rag_summarize(query)

@tool(description='读取当前求职者资料')
def get_candidate_profile() -> str: return serialize(get_profile())

@tool(description='更新求职者资料')
def update_candidate_profile(name: str='', target_roles: str='', target_cities: str='', skills: str='', resume_summary: str='') -> str: return serialize(update_profile(**{k:v for k,v in locals().items() if v}))

@tool(description='保存招聘岗位')
def save_job(company: str, title: str, description: str, city: str='', source: str='manual') -> str: return serialize(add_job(company,title,description,city,source))

@tool(description='列出招聘岗位')
def get_jobs(status: str='') -> str: return serialize(list_jobs(status))

def _parse_jd_structured(jd_text: str) -> dict:
    import json
    from model.factory import chat_model
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import PromptTemplate
    prompt = PromptTemplate.from_template(PARSE_JD_STRUCTURED_PROMPT)
    chain = prompt | chat_model | StrOutputParser()
    result_str = chain.invoke({"jd_text": jd_text})
    try:
        parsed = _extract_json(result_str)
        parsed["parse_ok"] = True
        return parsed
    except json.JSONDecodeError:
        return {"parse_ok": False, "error": result_str[:300]}

def _match_skill_list(skills_from_jd, candidate_text):
    candidate_lower = candidate_text.lower()
    matched = []
    missing = []
    for skill in skills_from_jd:
        skill_lower = skill.lower().strip()
        if not skill_lower:
            continue
        if skill_lower in candidate_lower or any(alias in candidate_lower for alias in _skill_aliases(skill_lower)):
            matched.append(skill)
        else:
            missing.append(skill)
    return matched, missing

def _skill_aliases(skill):
    alias_map = {
        'python': ['python3', 'py'],
        'langchain': ['langchain'],
        'langgraph': ['langgraph'],
        'rag': ['检索增强', '检索增强生成', 'retrieval-augmented'],
        'fastapi': ['fast api'],
        'docker': ['容器化', 'container'],
        'linux': ['ubuntu', 'centos'],
        'sql': ['mysql', 'postgresql', 'sqlite', '数据库'],
        'git': ['github', 'gitlab', '版本控制'],
        'ci/cd': ['持续集成', '持续部署', 'github actions'],
        'llm': ['大模型', '大语言模型', 'large language model'],
        'embedding': ['向量化', '向量表示'],
        'prompt': ['提示词', 'prompt engineering'],
        'transformer': ['注意力机制', 'attention'],
        'pytorch': ['torch'],
        '深度学习': ['deep learning', 'dl'],
        '机器学习': ['machine learning', 'ml'],
    }
    return alias_map.get(skill, [])

@tool(description='分析岗位匹配度，自动拆解岗位要求为学历/城市/技能/经验/加分项等维度，逐项与候选人资料匹配并给出加权总分和针对性建议')
def analyze_job_match(job_id: int) -> str:
    job = get_job(job_id)
    if not job: return '未找到该岗位'
    profile = get_profile()
    candidate_text = (profile.get('skills','') + ' ' + profile.get('resume_summary','')).lower()
    candidate_name = profile.get('name', '求职者')
    jd_text = job['description']
    jd_parsed = _parse_jd_structured(jd_text)
    if not jd_parsed.get('parse_ok'):
        return serialize({'job': f"{job['company']} - {job['title']}", 'error': 'JD 拆解失败，LLM 输出格式异常', 'raw_error': jd_parsed.get('error', '')})
    breakdown = {}
    total_weight = 0
    total_score = 0
    all_matched = []
    all_missing = []
    education = jd_parsed.get('education', '未明确')
    edu_required = jd_parsed.get('education_required', False)
    # LLM 可能返回 null，get 的默认值不会兜住 null，统一用 or [] 兜底
    cities = jd_parsed.get('cities') or []
    exp = jd_parsed.get('experience_years', '未明确')
    exp_required = jd_parsed.get('experience_required', False)
    must_skills = jd_parsed.get('must_have_skills') or []
    nice_skills = jd_parsed.get('nice_to_have_skills') or []
    must_quals = jd_parsed.get('must_have_qualifications') or []
    nice_quals = jd_parsed.get('nice_to_have_qualifications') or []
    edu_match = True
    edu_note = ''
    if education != '未明确':
        resume_summary = profile.get('resume_summary', '')
        if '硕士' in education or '研究生' in education:
            if '硕士' in resume_summary or '研究生' in resume_summary:
                edu_note = '学历匹配：岗位要求硕士，简历中有硕士背景'
            else:
                edu_match = False
                edu_note = '学历可能不匹配：岗位要求硕士，简历中未明确提及'
        elif '本科' in education:
            edu_note = '学历基本匹配：岗位要求本科及以上'
        else:
            edu_note = f'学历要求：{education}'
    else:
        edu_note = '学历要求未明确'
    edu_score = 100 if edu_match else (40 if edu_required else 70)
    if education != '未明确':
        breakdown['学历'] = {'required': education, 'hard_requirement': edu_required, 'matched': edu_match, 'score': edu_score, 'note': edu_note}
        weight = 15 if edu_required else 5
        total_weight += weight
        total_score += edu_score * weight
    city_match = True
    city_note = ''
    target_cities = [c.strip() for c in profile.get('target_cities', '').split(',') if c.strip()]
    if cities:
        overlap = [c for c in cities if any(tc in c or c in tc for tc in target_cities)]
        if overlap:
            city_note = f'城市匹配：{", ".join(overlap)}'
            city_match = True
        else:
            city_note = f'城市不匹配：岗位要求{", ".join(cities)}，你的目标城市是{", ".join(target_cities) if target_cities else "未设置"}'
            city_match = False
        city_score = 100 if city_match else 30
        breakdown['城市'] = {'required': cities, 'matched': overlap if city_match else [], 'gaps': [] if city_match else cities, 'score': city_score, 'note': city_note}
        total_weight += 5
        total_score += city_score * 5
    if exp != '未明确':
        exp_note = f'经验要求：{exp}'
        if '应届' in exp:
            exp_score = 100
            exp_note += '（应届可，完全匹配）'
        else:
            exp_score = 60
            exp_note += '（请确认自身经验是否满足）'
        breakdown['经验'] = {'required': exp, 'hard_requirement': exp_required, 'score': exp_score, 'note': exp_note}
        weight = 10 if exp_required else 5
        total_weight += weight
        total_score += exp_score * weight
    if must_skills:
        m_hit, m_gap = _match_skill_list(must_skills, candidate_text)
        m_score = round(100 * len(m_hit) / len(must_skills)) if must_skills else 100
        breakdown['必须技能'] = {'required': must_skills, 'matched': m_hit, 'gaps': m_gap, 'score': m_score, 'note': f'匹配 {len(m_hit)}/{len(must_skills)} 项必须技能'}
        all_matched.extend(m_hit)
        all_missing.extend(m_gap)
        total_weight += 40
        total_score += m_score * 40
    if nice_skills:
        n_hit, n_gap = _match_skill_list(nice_skills, candidate_text)
        n_score = round(100 * len(n_hit) / len(nice_skills)) if nice_skills else 100
        breakdown['加分技能'] = {'required': nice_skills, 'matched': n_hit, 'gaps': n_gap, 'score': n_score, 'note': f'匹配 {len(n_hit)}/{len(nice_skills)} 项加分技能'}
        all_matched.extend(n_hit)
        all_missing.extend(n_gap)
        total_weight += 15
        total_score += n_score * 15
    if must_quals:
        mq_hit, mq_gap = _match_skill_list(must_quals, candidate_text)
        mq_score = round(100 * len(mq_hit) / len(must_quals)) if must_quals else 100
        breakdown['必须条件'] = {'required': must_quals, 'matched': mq_hit, 'gaps': mq_gap, 'score': mq_score, 'note': f'匹配 {len(mq_hit)}/{len(must_quals)} 项必须条件'}
        all_matched.extend(mq_hit)
        all_missing.extend(mq_gap)
        total_weight += 15
        total_score += mq_score * 15
    if nice_quals:
        nq_hit, nq_gap = _match_skill_list(nice_quals, candidate_text)
        nq_score = round(100 * len(nq_hit) / len(nice_quals)) if nice_quals else 100
        breakdown['加分条件'] = {'required': nice_quals, 'matched': nq_hit, 'gaps': nq_gap, 'score': nq_score, 'note': f'匹配 {len(nq_hit)}/{len(nice_quals)} 项加分条件'}
        all_matched.extend(nq_hit)
        all_missing.extend(nq_gap)
        total_weight += 10
        total_score += nq_score * 10
    if total_weight == 0:
        total_weight = 1
    overall_score = round(total_score / total_weight)
    advice_parts = []
    if not edu_match and edu_required:
        advice_parts.append('学历是硬性要求且可能不匹配，但技能匹配度高仍可尝试，建议在简历中突出相关项目经验。')
    elif not edu_match:
        advice_parts.append('学历非硬性要求，技能匹配度更重要，建议重点突出项目经历。')
    if all_missing:
        gap_must = [s for s in all_missing if s in must_skills or s in must_quals]
        gap_nice = [s for s in all_missing if s in nice_skills or s in nice_quals]
        if gap_must:
            advice_parts.append(f'必须技能缺口：{", ".join(gap_must)}，建议优先补充。')
        if gap_nice:
            advice_parts.append(f'加分项缺口：{", ".join(gap_nice)}，有的话会更有竞争力。')
    if not advice_parts:
        advice_parts.append('匹配度较高，建议准备针对性面试题，重点展示匹配技能的项目经验。')
    vector_evidence = []
    try:
        must_skills = must_skills or []
        nice_skills = nice_skills or []
        jd_query = f"{job['company']} {job['title']} {' '.join(must_skills + nice_skills)}"
        raw_evidence = vector_match_evidence(jd_query, top_k=5)
        if raw_evidence:
            reranked = rerank_with_llm(jd_query, raw_evidence)
            for item in reranked.get('ranked_evidence', []):
                idx = item.get('index', 0)
                if idx < len(raw_evidence):
                    vector_evidence.append({
                        'source': raw_evidence[idx]['source'],
                        'content': raw_evidence[idx]['content'][:150],
                        'similarity': raw_evidence[idx].get('similarity', 0),
                        'relevance_score': item.get('relevance_score', 0),
                        'reason': item.get('reason', '')
                    })
    except Exception as e:
        # 向量证据是锦上添花，失败不影响结构化打分，但必须留痕，否则问题会被静默吞掉
        logger.warning(f"[匹配分析]向量证据生成失败：{str(e)[:200]}")
    return serialize({
        'job': f"{job['company']} - {job['title']}",
        'job_category': jd_parsed.get('job_category', ''),
        'jd_summary': jd_parsed.get('summary', ''),
        'score': overall_score,
        'breakdown': breakdown,
        'matched_skills': sorted(set(all_matched)),
        'gaps': sorted(set(all_missing)),
        'evidence': f'已在{candidate_name}的资料中找到 {len(set(all_matched))} 项匹配' if all_matched else '候选人资料中暂未找到明确匹配证据',
        'vector_evidence': vector_evidence,
        'advice': ' '.join(advice_parts)
    })

@tool(description='根据指定岗位和候选人资料生成面试准备重点与问题')
def generate_interview_prep(job_id: int) -> str:
    import json
    from model.factory import chat_model
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import PromptTemplate

    job = get_job(job_id)
    if not job:
        return serialize({'error': f'未找到 ID 为 {job_id} 的岗位'})

    profile = get_profile()
    jd_text = (job.get('description') or '')[:1500]

    # 先拆解 JD，拿到必须/加分技能，让面试题能落到具体技能点上
    jd_parsed = _parse_jd_structured(jd_text)
    if not jd_parsed.get('parse_ok'):
        jd_parsed = {}

    prompt = PromptTemplate.from_template(INTERVIEW_PREP_PROMPT)
    chain = prompt | chat_model | StrOutputParser()

    try:
        raw = chain.invoke({
            'job_category': jd_parsed.get('job_category') or '软件研发',
            'company': job['company'],
            'title': job['title'],
            'must_skills': '、'.join(jd_parsed.get('must_have_skills') or []) or '未明确',
            'nice_skills': '、'.join(jd_parsed.get('nice_to_have_skills') or []) or '未明确',
            'education': jd_parsed.get('education') or '未明确',
            'experience': jd_parsed.get('experience_years') or '未明确',
            'jd_text': jd_text,
            'skills': profile.get('skills') or '未填写',
            'resume_summary': (profile.get('resume_summary') or '')[:800],
        })
        parsed = _extract_json(raw)
    except Exception as e:
        logger.error(f"[面试准备]生成失败：{str(e)[:200]}")
        return serialize({
            'job': f"{job['company']} - {job['title']}",
            'error': '面试准备生成失败，请稍后重试',
            'detail': str(e)[:150],
        })

    return serialize({
        'job': f"{job['company']} - {job['title']}",
        'job_category': jd_parsed.get('job_category', ''),
        'strategy': parsed.get('strategy', ''),
        'focus': parsed.get('focus', []),
        'questions': parsed.get('questions', []),
        'gaps': parsed.get('gaps', []),
        'resume_evidence': (profile.get('resume_summary') or '')[:300],
    })

@tool(description='把岗位加入投递跟踪')
def track_application(job_id: int, status: str='已收藏', notes: str='') -> str: return serialize(add_application(job_id,status,notes))

@tool(description='查看投递记录')
def get_application_tracker() -> str: return serialize(list_applications())

@tool(description='更新投递记录状态，例如已投递、笔试、面试、Offer、拒绝或暂停')
def update_application_status(application_id: int, status: str, notes: str='') -> str: return serialize(update_application(application_id, status, notes))

@tool(description='记录面试安排，可包含面试轮次、面试问题、自我评价和复盘')
def schedule_interview(job_id: int, interview_date: str='', stage: str='待安排', round_num: int=1, questions: str='', self_eval: str='', review: str='', notes: str='') -> str: return serialize(add_interview(job_id,interview_date,stage,round_num,questions,self_eval,review,notes))

@tool(description='查看所有面试记录，包括面试轮次、问题、自我评价和复盘')
def get_interview_records() -> str: return serialize(list_interviews())

@tool(description='对指定面试记录进行复盘分析，根据面试问题和自我评价生成改进建议')
def review_interview(interview_id: int) -> str:
    interview = get_interview(interview_id)
    if not interview:
        return serialize({"error": "未找到该面试记录"})
    if not interview.get("questions") and not interview.get("self_eval"):
        return serialize({"error": "该面试记录没有面试问题或自我评价，请先补充后再复盘"})
    import json
    from model.factory import chat_model
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import PromptTemplate
    profile = get_profile()
    prompt = PromptTemplate.from_template(INTERVIEW_REVIEW_PROMPT)
    chain = prompt | chat_model | StrOutputParser()
    result_str = chain.invoke({
        "company": interview.get("company", "未知"),
        "title": interview.get("title", "未知"),
        "round_num": interview.get("round_num", 1),
        "questions": interview.get("questions", "未记录"),
        "self_eval": interview.get("self_eval", "未记录"),
        "skills": profile.get("skills", ""),
        "resume_summary": profile.get("resume_summary", "")[:500]
    })
    try:
        parsed = _extract_json(result_str)
        review_text = json.dumps(parsed, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        review_text = result_str[:500]
    update_interview(interview_id, review=review_text)
    interview = get_interview(interview_id)
    return serialize(interview)

@tool(description='添加求职任务提醒，如"准备XX公司笔试"、"跟进XX公司HR"等')
def add_task_reminder(job_id: int, task_type: str='待办', description: str='', due_date: str='', status: str='待完成') -> str: return serialize(add_task(job_id,task_type,description,due_date,status))

@tool(description='查看求职任务列表，可按状态筛选（待完成/已完成/全部）')
def get_task_list(status: str='') -> str: return serialize(list_tasks(status))

@tool(description='更新求职任务状态，标记为已完成或修改描述和截止日期')
def update_task_status(task_id: int, status: str='', description: str='', due_date: str='') -> str:
    kwargs = {}
    if status: kwargs['status'] = status
    if description: kwargs['description'] = description
    if due_date: kwargs['due_date'] = due_date
    return serialize(update_task(task_id, **kwargs))

@tool(description='将候选人资料（技能、简历摘要、目标岗位）同步到向量数据库，用于语义匹配检索')
def sync_candidate_vector() -> str: return sync_candidate_to_vector()

@tool(description='将岗位描述同步到向量数据库，可指定单个岗位ID或同步全部岗位')
def sync_job_vector(job_id: int=0) -> str: return sync_job_to_vector(job_id if job_id else None)

@tool(description='创建简历版本，可指定版本名称、目标岗位类型、技能、摘要、项目经历和教育背景')
def create_resume_version(version_name: str, target_type: str='通用', skills: str='', resume_summary: str='', projects: str='', education: str='') -> str:
    return serialize(add_resume(version_name, target_type, skills, resume_summary, projects, education))

@tool(description='查看所有简历版本列表')
def list_resume_versions() -> str: return serialize(list_resumes())

@tool(description='获取当前激活的简历版本')
def get_current_resume() -> str:
    r = get_active_resume()
    return serialize(r) if r else serialize({'info': '没有激活的简历版本'})

@tool(description='切换激活的简历版本，设为当前使用的简历')
def switch_resume_version(resume_id: int) -> str: return serialize(set_active_resume(resume_id))

@tool(description='根据岗位类型推荐最合适的简历版本，并导出为Word文档')
def export_resume_for_job(job_id: int) -> str:
    return _export_resume_impl(job_id)


@tool(description='从招聘网站复制的岗位描述文本中智能提取公司、岗位、城市和描述，并保存到数据库')
def parse_and_save_job(raw_text: str) -> str:
    import json
    from model.factory import chat_model
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import PromptTemplate
    prompt = PromptTemplate.from_template(PARSE_JOB_TEXT_PROMPT)
    chain = prompt | chat_model | StrOutputParser()
    result_str = chain.invoke({"raw_text": raw_text})
    return _save_parsed_job(result_str, raw_text, "智能解析")

def _save_parsed_job(result_str: str, fallback_text: str, source: str) -> str:
    import json
    try:
        parsed = _extract_json(result_str)
        company = parsed.get("company", "未知")
        title = parsed.get("title", "未知")
        city = parsed.get("city", "")
        description = parsed.get("description", fallback_text)
        job = add_job(company, title, description, city, source=source)
        return serialize({"status": "success", "job_id": job.get("id"), "company": company, "title": title, "city": city})
    except json.JSONDecodeError:
        return serialize({"status": "parse_error", "raw_llm_output": result_str[:500], "advice": "LLM 输出不是合法 JSON，请手动录入岗位信息"})

def _extract_json(text: str) -> dict:
    import json
    if "`json" in text:
        text = text.split("`json")[1].split("`")[0]
    elif "`" in text:
        text = text.split("`")[1].split("`")[0]
    return json.loads(text.strip())

def parse_job_text(raw_text: str) -> dict:
    import json
    from model.factory import chat_model
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import PromptTemplate
    prompt = PromptTemplate.from_template(PARSE_JOB_TEXT_PROMPT)
    chain = prompt | chat_model | StrOutputParser()
    result_str = chain.invoke({"raw_text": raw_text})
    try:
        parsed = _extract_json(result_str)
        parsed["parse_ok"] = True
        return parsed
    except json.JSONDecodeError:
        return {"parse_ok": False, "company": "", "title": "", "city": "", "description": raw_text, "error": result_str[:300]}

def parse_job_image(image_bytes: bytes) -> dict:
    import json, base64
    from model.factory import vision_model
    from langchain_core.messages import HumanMessage
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    # OpenAI 兼容接口要求 image_url 结构（原生 DashScope 用的是 {"type":"image","image":...}）
    # 同时按文件头判断真实 mime：原来写死 jpeg，上传 png 截图时 mime 与内容不符
    mime = "image/png" if image_bytes[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
    message = HumanMessage(content=[
        {"type": "text", "text": PARSE_JOB_IMAGE_PROMPT},
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
    ])
    response = vision_model.invoke([message])
    result_str = response.content
    if isinstance(result_str, list):
        result_str = " ".join(
            item["text"] if isinstance(item, dict) and "text" in item else str(item)
            for item in result_str
        )
    try:
        parsed = _extract_json(result_str)
        parsed["parse_ok"] = True
        return parsed
    except json.JSONDecodeError:
        return {"parse_ok": False, "company": "", "title": "", "city": "", "description": "", "error": result_str[:300]}

def extract_text_from_pdf(file_bytes: bytes) -> str:
    # PyMuPDF >= 1.24 的官方模块名是 pymupdf，旧名 fitz 已标记弃用
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)

def extract_text_from_docx(file_bytes: bytes) -> str:
    import io
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    text_parts = []
    for para in doc.paragraphs:
        if para.text.strip():
            text_parts.append(para.text.strip())
    for table in doc.tables:
        for row in table.rows:
            row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_text:
                text_parts.append(" | ".join(row_text))
    return "\n".join(text_parts)

def parse_resume_text(resume_text: str) -> dict:
    import json
    from model.factory import chat_model
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import PromptTemplate
    prompt = PromptTemplate.from_template(PARSE_RESUME_PROMPT)
    chain = prompt | chat_model | StrOutputParser()
    result_str = chain.invoke({"resume_text": resume_text})
    try:
        parsed = _extract_json(result_str)
        parsed["parse_ok"] = True
        return parsed
    except json.JSONDecodeError:
        return {"parse_ok": False, "name": "", "target_roles": "", "target_cities": "", "skills": "", "resume_summary": "", "error": result_str[:300]}

def parse_resume_file(file_bytes: bytes, filename: str) -> dict:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf":
        text = extract_text_from_pdf(file_bytes)
    elif ext in ("docx", "doc"):
        text = extract_text_from_docx(file_bytes)
    else:
        return {"parse_ok": False, "error": f"不支持的文件格式: .{ext}，请上传 PDF 或 Word 文件"}
    if not text.strip():
        return {"parse_ok": False, "error": "文件内容为空，可能是扫描版 PDF（请尝试截图上传）或空文档"}
    result = parse_resume_text(text)
    result["raw_text_length"] = len(text)
    return result

def _export_resume_impl(job_id):
    import json, os
    job = get_job(job_id)
    if not job:
        return serialize({'error': '未找到该岗位'})
    resumes = list_resumes()
    if not resumes:
        profile = get_profile()
        resume_data = {'version_name': '默认简历', 'skills': profile.get('skills', ''), 'resume_summary': profile.get('resume_summary', ''), 'projects': '', 'education': ''}
    else:
        from model.factory import chat_model
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import PromptTemplate
        resume_list_text = ''
        for r in resumes:
            resume_list_text += f"\n版本ID={r['id']}: {r['version_name']} (目标类型: {r.get('target_type','通用')}, 技能: {r.get('skills','')[:100]})"
        rec_prompt = (
            '根据岗位信息，从候选简历版本中选择最合适的一个。\n\n'
            '岗位：{company} - {title}\n'
            '岗位描述：{jd}\n\n'
            '候选简历版本：{resume_list}\n\n'
            '请以 JSON 返回：\n'
            '{{\n'
            '  "recommended_id": 推荐的简历版本ID,\n'
            '  "reason": "推荐原因"\n'
            '}}'
        )
        prompt = PromptTemplate.from_template(rec_prompt)
        chain = prompt | chat_model | StrOutputParser()
        result_str = chain.invoke({'company': job['company'], 'title': job['title'], 'jd': job.get('description', '')[:500], 'resume_list': resume_list_text})
        try:
            start = result_str.find('{')
            end = result_str.rfind('}') + 1
            rec = json.loads(result_str[start:end])
            rec_id = rec.get('recommended_id')
        except (json.JSONDecodeError, ValueError):
            rec_id = resumes[0]['id'] if resumes else None
        chosen = get_resume(rec_id) if rec_id else None
        if not chosen:
            chosen = resumes[0]
        resume_data = chosen
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'picture')
    os.makedirs(output_dir, exist_ok=True)
    safe_name = ''.join(c for c in f"{job['company']}_{job['title']}" if c.isalnum() or c in '_ ')
    filename = f'简历_{safe_name}_{resume_data.get("version_name", "默认")}.docx'
    filepath = os.path.join(output_dir, filename)
    try:
        from docx import Document
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        doc = Document()
        style = doc.styles['Normal']
        style.font.size = Pt(11)
        profile = get_profile()
        name_para = doc.add_paragraph()
        name_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        name_run = name_para.add_run(profile.get('name', '求职者'))
        name_run.bold = True
        name_run.font.size = Pt(18)
        target_roles = profile.get('target_roles', '')
        target_cities = profile.get('target_cities', '')
        if target_roles or target_cities:
            info_para = doc.add_paragraph()
            info_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            info_parts = []
            if target_roles: info_parts.append(f'目标岗位：{target_roles}')
            if target_cities: info_parts.append(f'目标城市：{target_cities}')
            info_para.add_run(' | '.join(info_parts))
        doc.add_paragraph()
        doc.add_heading('技能', level=2)
        skills_text = resume_data.get('skills', '')
        if skills_text:
            for skill in skills_text.split(','):
                skill = skill.strip()
                if skill:
                    doc.add_paragraph(skill, style='List Bullet')
        doc.add_heading('项目经历', level=2)
        projects_text = resume_data.get('projects', '')
        if projects_text:
            for proj in projects_text.split('\n'):
                proj = proj.strip()
                if proj:
                    if proj.startswith('-') or proj.startswith('\u2022'):
                        doc.add_paragraph(proj.lstrip('-\u2022 '), style='List Bullet')
                    else:
                        doc.add_paragraph(proj)
        else:
            summary = resume_data.get('resume_summary', '')
            if summary:
                doc.add_paragraph(summary)
        doc.add_heading('教育背景', level=2)
        edu_text = resume_data.get('education', '')
        if edu_text:
            for line in edu_text.split('\n'):
                line = line.strip()
                if line:
                    doc.add_paragraph(line)
        doc.save(filepath)
        return serialize({'message': '简历已导出', 'version': resume_data.get('version_name', '默认'), 'file': filepath, 'job': f"{job['company']} - {job['title']}"})
    except Exception as e:
        return serialize({'error': f'导出失败：{str(e)}', 'resume_data_keys': list(resume_data.keys())})

