from __future__ import annotations
import json, sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent / "career_pilot.db"

def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    with _connect() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY CHECK(id=1), name TEXT NOT NULL DEFAULT '求职者', target_roles TEXT NOT NULL DEFAULT '', target_cities TEXT NOT NULL DEFAULT '', skills TEXT NOT NULL DEFAULT '', resume_summary TEXT NOT NULL DEFAULT '', _source TEXT DEFAULT 'manual');
        CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT NOT NULL, title TEXT NOT NULL, city TEXT DEFAULT '', description TEXT NOT NULL, source TEXT DEFAULT 'manual', status TEXT NOT NULL DEFAULT '待评估', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS applications (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL REFERENCES jobs(id), status TEXT NOT NULL DEFAULT '已收藏', notes TEXT DEFAULT '', updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS interviews (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER REFERENCES jobs(id), interview_date TEXT DEFAULT '', stage TEXT DEFAULT '待安排', round_num INTEGER DEFAULT 1, questions TEXT DEFAULT '', self_eval TEXT DEFAULT '', review TEXT DEFAULT '', notes TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS chat_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER REFERENCES jobs(id), task_type TEXT NOT NULL DEFAULT '待办', description TEXT NOT NULL, due_date TEXT DEFAULT '', status TEXT NOT NULL DEFAULT '待完成', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS resumes (id INTEGER PRIMARY KEY AUTOINCREMENT, version_name TEXT NOT NULL, target_type TEXT DEFAULT '通用', skills TEXT DEFAULT '', resume_summary TEXT DEFAULT '', projects TEXT DEFAULT '', education TEXT DEFAULT '', is_active INTEGER DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        INSERT OR IGNORE INTO profile(id) VALUES(1);
        ''')
        try:
            conn.execute("ALTER TABLE profile ADD COLUMN _source TEXT DEFAULT 'manual'")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE interviews ADD COLUMN round_num INTEGER DEFAULT 1")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE interviews ADD COLUMN questions TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE interviews ADD COLUMN self_eval TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE interviews ADD COLUMN review TEXT DEFAULT ''")
        except Exception:
            pass

def _rows(sql, params=()):
    init_db()
    with _connect() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]

def get_profile():
    return _rows('SELECT * FROM profile WHERE id=1')[0]

def update_profile(**fields):
    allowed = {'name','target_roles','target_cities','skills','resume_summary'}
    values = {k: str(v) for k,v in fields.items() if k in allowed and v is not None}
    if values:
        with _connect() as conn:
            conn.execute('UPDATE profile SET ' + ', '.join(f'{k}=?' for k in values) + ' WHERE id=1', list(values.values()))
    return get_profile()

def add_job(company, title, description, city='', source='manual'):
    init_db()
    with _connect() as conn:
        cur = conn.execute('INSERT INTO jobs(company,title,city,description,source) VALUES(?,?,?,?,?)', (company,title,city,description,source))
        return dict(conn.execute('SELECT * FROM jobs WHERE id=?', (cur.lastrowid,)).fetchone())

def list_jobs(status=''):
    return _rows("SELECT * FROM jobs WHERE (?='' OR status=?) ORDER BY id DESC", (status,status))

def get_job(job_id):
    rows = _rows('SELECT * FROM jobs WHERE id=?', (job_id,))
    return rows[0] if rows else None

def add_application(job_id, status='已收藏', notes=''):
    init_db()
    with _connect() as conn:
        cur = conn.execute('INSERT INTO applications(job_id,status,notes) VALUES(?,?,?)', (job_id,status,notes))
        return dict(conn.execute('SELECT a.*,j.company,j.title FROM applications a JOIN jobs j ON j.id=a.job_id WHERE a.id=?', (cur.lastrowid,)).fetchone())

def list_applications():
    return _rows('SELECT a.*,j.company,j.title,j.city FROM applications a JOIN jobs j ON j.id=a.job_id ORDER BY a.updated_at DESC')

def update_application(application_id, status=None, notes=None):
    init_db()
    values = {'status': status, 'notes': notes}
    values = {k: v for k, v in values.items() if v is not None}
    if values:
        with _connect() as conn:
            conn.execute('UPDATE applications SET ' + ', '.join(f'{k}=?' for k in values) + ', updated_at=CURRENT_TIMESTAMP WHERE id=?', [*values.values(), application_id])
    rows = _rows('SELECT a.*,j.company,j.title,j.city FROM applications a JOIN jobs j ON j.id=a.job_id WHERE a.id=?', (application_id,))
    return rows[0] if rows else None

def add_interview(job_id, interview_date='', stage='待安排', round_num=1, questions='', self_eval='', review='', notes=''):
    init_db()
    with _connect() as conn:
        cur = conn.execute('INSERT INTO interviews(job_id,interview_date,stage,round_num,questions,self_eval,review,notes) VALUES(?,?,?,?,?,?,?,?)', (job_id,interview_date,stage,round_num,questions,self_eval,review,notes))
        return dict(conn.execute('SELECT i.*,j.company,j.title FROM interviews i JOIN jobs j ON j.id=i.job_id WHERE i.id=?', (cur.lastrowid,)).fetchone())

def list_interviews():
    return _rows('SELECT i.*,j.company,j.title,j.city FROM interviews i JOIN jobs j ON j.id=i.job_id ORDER BY i.id DESC')

def get_interview(interview_id):
    rows = _rows('SELECT i.*,j.company,j.title,j.city,j.description FROM interviews i JOIN jobs j ON j.id=i.job_id WHERE i.id=?', (interview_id,))
    return rows[0] if rows else None

def update_interview(interview_id, interview_date=None, stage=None, round_num=None, questions=None, self_eval=None, review=None, notes=None):
    init_db()
    values = {}
    if interview_date is not None: values['interview_date'] = interview_date
    if stage is not None: values['stage'] = stage
    if round_num is not None: values['round_num'] = round_num
    if questions is not None: values['questions'] = questions
    if self_eval is not None: values['self_eval'] = self_eval
    if review is not None: values['review'] = review
    if notes is not None: values['notes'] = notes
    if values:
        with _connect() as conn:
            conn.execute('UPDATE interviews SET ' + ', '.join(f'{k}=?' for k in values) + ' WHERE id=?', [*values.values(), interview_id])
    rows = _rows('SELECT i.*,j.company,j.title,j.city FROM interviews i JOIN jobs j ON j.id=i.job_id WHERE i.id=?', (interview_id,))
    return rows[0] if rows else None

def add_task(job_id, task_type='待办', description='', due_date='', status='待完成'):
    init_db()
    with _connect() as conn:
        cur = conn.execute('INSERT INTO tasks(job_id,task_type,description,due_date,status) VALUES(?,?,?,?,?)', (job_id,task_type,description,due_date,status))
        return dict(conn.execute('SELECT t.*,j.company,j.title FROM tasks t JOIN jobs j ON j.id=t.job_id WHERE t.id=?', (cur.lastrowid,)).fetchone())

def list_tasks(status=''):
    return _rows("SELECT t.*,j.company,j.title FROM tasks t JOIN jobs j ON j.id=t.job_id WHERE (?='' OR t.status=?) ORDER BY t.due_date ASC, t.id ASC", (status, status))

def update_task(task_id, status=None, description=None, due_date=None):
    init_db()
    values = {}
    if status is not None: values['status'] = status
    if description is not None: values['description'] = description
    if due_date is not None: values['due_date'] = due_date
    if values:
        with _connect() as conn:
            conn.execute('UPDATE tasks SET ' + ', '.join(f'{k}=?' for k in values) + ' WHERE id=?', [*values.values(), task_id])
    rows = _rows('SELECT t.*,j.company,j.title FROM tasks t JOIN jobs j ON j.id=t.job_id WHERE t.id=?', (task_id,))
    return rows[0] if rows else None

def add_resume(version_name, target_type='通用', skills='', resume_summary='', projects='', education='', is_active=0):
    init_db()
    with _connect() as conn:
        cur = conn.execute('INSERT INTO resumes(version_name,target_type,skills,resume_summary,projects,education,is_active) VALUES(?,?,?,?,?,?,?)', (version_name,target_type,skills,resume_summary,projects,education,is_active))
        return dict(conn.execute('SELECT * FROM resumes WHERE id=?', (cur.lastrowid,)).fetchone())

def list_resumes():
    return _rows('SELECT * FROM resumes ORDER BY is_active DESC, id DESC')

def get_resume(resume_id):
    rows = _rows('SELECT * FROM resumes WHERE id=?', (resume_id,))
    return rows[0] if rows else None

def get_active_resume():
    rows = _rows('SELECT * FROM resumes WHERE is_active=1 LIMIT 1')
    return rows[0] if rows else None

def update_resume(resume_id, version_name=None, target_type=None, skills=None, resume_summary=None, projects=None, education=None, is_active=None):
    init_db()
    values = {}
    if version_name is not None: values['version_name'] = version_name
    if target_type is not None: values['target_type'] = target_type
    if skills is not None: values['skills'] = skills
    if resume_summary is not None: values['resume_summary'] = resume_summary
    if projects is not None: values['projects'] = projects
    if education is not None: values['education'] = education
    if is_active is not None: values['is_active'] = is_active
    if values:
        with _connect() as conn:
            conn.execute('UPDATE resumes SET ' + ', '.join(f'{k}=?' for k in values) + ' WHERE id=?', [*values.values(), resume_id])
    rows = _rows('SELECT * FROM resumes WHERE id=?', (resume_id,))
    return rows[0] if rows else None

def set_active_resume(resume_id):
    init_db()
    with _connect() as conn:
        conn.execute('UPDATE resumes SET is_active=0 WHERE is_active=1')
        conn.execute('UPDATE resumes SET is_active=1 WHERE id=?', (resume_id,))
    return get_resume(resume_id)

def delete_resume(resume_id):
    init_db()
    with _connect() as conn:
        conn.execute('DELETE FROM resumes WHERE id=?', (resume_id,))

def save_message(role: str, content: str):
    init_db()
    with _connect() as conn:
        conn.execute('INSERT INTO chat_messages(role, content) VALUES(?,?)', (role, content))

def load_messages() -> list[dict]:
    return _rows('SELECT role, content FROM chat_messages ORDER BY id ASC')

def clear_messages():
    init_db()
    with _connect() as conn:
        conn.execute('DELETE FROM chat_messages')

def serialize(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)