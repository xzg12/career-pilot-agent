"""将捆绑的匿名简历和职位示例加载到 SQLite 中"""
import json
from pathlib import Path
from career_store import add_job, init_db, update_profile, list_jobs

ROOT = Path(__file__).resolve().parent

def main():
    init_db()
    resume = (ROOT / 'data/career/candidate_resume.txt').read_text(encoding='utf-8')
    update_profile(name='林默（示例）', target_roles='AI 应用开发工程师、Python 后端工程师', target_cities='杭州、深圳、上海', skills='Python、FastAPI、LangChain、LangGraph、RAG、Chroma、Streamlit、SQL、Docker、Git', resume_summary=resume)
    existing = {(j['company'], j['title']) for j in list_jobs()}
    for job in json.loads((ROOT / 'data/career/jobs.json').read_text(encoding='utf-8')):
        if (job['company'], job['title']) not in existing:
            add_job(job['company'], job['title'], job['description'], job.get('city',''), job.get('source','demo'))
    print(f'已加载示例候选人资料和 {len(list_jobs())} 条岗位')

if __name__ == '__main__':
    main()
