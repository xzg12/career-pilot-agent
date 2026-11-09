"""
为整个工程提供统一的绝对路径
"""
import os

def get_project_root() -> str:
    """
    获取工程所在的根目录
    :return: 字符串根目录
    """
    # 当前文件的绝对路径
    current_file= os.path.abspath(__file__)
    # 获取工程的根目录，
    # 先获取文件所在的文件夹的绝对路径
    current_dir=os.path.dirname(current_file)   #os.path.dirname() 提取路径中的目录部分（去掉最后的文件名）
    # 获取工程根目录，在 current_dir 的基础上再往上一级目录
    project_root=os.path.dirname(current_dir)

    return project_root

def get_abs_path(relative_path:str)->str:
    """
    传递相对路径，得到绝对路径
    :param relative_path:
    :return:
    """
    project_root=get_project_root()
    return os.path.join(project_root,relative_path)  #os.path.join() 将多个路径片段智能拼接成一个完整路径，自动处理路径分隔符（Windows 上是 \，Linux/Mac 上是 /）。

if __name__ == '__main__':
    print(get_abs_path("config/config.txt"))

