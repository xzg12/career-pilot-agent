r"""
读取 config/*.yml 配置。

yml
k : V

运行指令（在项目根目录执行，用于自检）：
    python -m utils.config_handler

"""
import yaml
from utils.path_tool import get_abs_path
# from path_tool import *     #这种导入方式不会出现错误提示

# 加载RAG配置
def load_rag_config(config_path: str = get_abs_path("config/rag.yml"), encoding: str = "utf-8"):
    with open(config_path, "r", encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)

# 加载Chroma（向量数据库）配置
def load_chroma_config(config_path: str = get_abs_path("config/chroma.yml"), encoding: str = "utf-8"):
    with open(config_path, "r", encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)

# 加载提示语配置
def load_prompts_config(config_path: str = get_abs_path("config/prompts.yml"), encoding: str = "utf-8"):
    with open(config_path, "r", encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)

# 加载代理配置
def load_agent_config(config_path: str = get_abs_path("config/agent.yml"), encoding: str = "utf-8"):
    with open(config_path, "r", encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)


rag_conf = load_rag_config()
chroma_conf = load_chroma_config()
agent_conf = load_agent_config()
prompts_conf = load_prompts_config()

if __name__ == '__main__':
    print(rag_conf["chat_model_name"])  # 输出对应配置

