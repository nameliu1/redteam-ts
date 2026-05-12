import os
import time
import datetime
import sys
import subprocess
import shutil

LOG_FILE_HANDLE = None
ORIGINAL_STDOUT = sys.stdout
ORIGINAL_STDERR = sys.stderr

class TeeStream:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()
        return len(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()

# 配置信息
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
URL_FILE = os.path.join(BASE_DIR, "url.txt")
DIR_FILE = os.path.join(BASE_DIR, "dirv2.txt")
JSON_FILE = os.path.join(BASE_DIR, "res.json")        # spray原始输出
EXCEL_FILE = os.path.join(BASE_DIR, "res_processed.xlsx")  # 处理后的Excel
TXT_FILE = os.path.join(BASE_DIR, "res_processed.txt")    # 提取的URL列表
HIDE_PYTHON_CONSOLE = True
MONITOR_INTERVAL = 5  # 进程监控间隔（秒）
STATUS_CODE_COL_INDEX = 9  # J列（Excel列索引从0开始，J列对应索引9）【Spray状态码结果在此列】
URL_COL_INDEX = 4  # E列（根据实际Excel列调整）
EHOLE_QUICK_TIMEOUT = 3  # ehole快速完成的超时时间（秒）

# 需要删除的过程文件列表
TO_DELETE_FILES = [
    os.path.join(BASE_DIR, "url.txt.stat"),
    os.path.join(BASE_DIR, "res_processed.txt")
]

def log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def setup_script_logging(log_dir):
    global LOG_FILE_HANDLE
    shared_log_path = os.environ.get("WORKFLOW_LOG_PATH")
    if shared_log_path:
        os.makedirs(os.path.dirname(shared_log_path), exist_ok=True)
        log_file_path = shared_log_path
    else:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file_path = generate_unique_filename(log_dir, f"1py_workflow_{timestamp}", ".log")
    LOG_FILE_HANDLE = open(log_file_path, "a", encoding="utf-8", buffering=1)
    sys.stdout = TeeStream(ORIGINAL_STDOUT, LOG_FILE_HANDLE)
    sys.stderr = TeeStream(ORIGINAL_STDERR, LOG_FILE_HANDLE)
    log(f"日志文件: {log_file_path}")


def teardown_script_logging():
    global LOG_FILE_HANDLE
    sys.stdout = ORIGINAL_STDOUT
    sys.stderr = ORIGINAL_STDERR
    if LOG_FILE_HANDLE:
        LOG_FILE_HANDLE.close()
        LOG_FILE_HANDLE = None

def hide_python_console():
    if HIDE_PYTHON_CONSOLE:
        try:
            import win32gui, win32con
            hwnd = win32gui.GetForegroundWindow()
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
        except:
            log("警告: 无法隐藏 Python 控制台窗口")

def format_command(args):
    return subprocess.list2cmdline(args)


def run_native_command(args, process_name):
    log(f"执行命令: {format_command(args)}")
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)

    try:
        process = subprocess.Popen(
            args,
            cwd=BASE_DIR,
            creationflags=creationflags
        )
        log(f"已启动进程: {process_name} (PID: {process.pid})")
        return process
    except Exception as e:
        log(f"启动 {process_name} 失败: {e}")
        return None


def monitor_process(process, process_name, timeout=3600):
    if process is None:
        log(f"错误: {process_name} 进程未成功启动")
        return False

    log(f"监控进程: {process_name} (PID: {process.pid})")
    start_time = time.time()

    while time.time() - start_time < timeout:
        return_code = process.poll()
        if return_code is not None:
            log(f"进程已结束: {process_name} (PID: {process.pid}, 返回码: {return_code})")
            return return_code == 0
        time.sleep(1)

    log(f"错误: {process_name} 运行超时，PID: {process.pid}")
    try:
        process.terminate()
    except Exception as e:
        log(f"终止超时进程失败: {e}")
    return False

def wait_for_file(file_path, timeout=300):
    log(f"等待文件生成: {file_path}")
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(file_path):
            log(f"文件已生成: {file_path}")
            return True
        time.sleep(1)
    log(f"错误: 文件未生成: {file_path}")
    return False

# 生成不冲突的文件名
def generate_unique_filename(base_dir, base_name, ext):
    counter = 1
    original_name = f"{base_name}{ext}"
    full_path = os.path.join(base_dir, original_name)
    
    # 如果文件已存在，则添加序号后缀
    while os.path.exists(full_path):
        new_name = f"{base_name}_{counter}{ext}"
        full_path = os.path.join(base_dir, new_name)
        counter += 1
    
    return full_path

# 删除指定的过程文件
def clean_process_files():
    log("开始清理上次运行的过程文件...")
    for file_path in TO_DELETE_FILES:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                log(f"已删除: {file_path}")
            except Exception as e:
                log(f"删除文件 {file_path} 时出错: {e}")
        else:
            log(f"文件不存在，跳过删除: {file_path}")
    log("过程文件清理完成")

def process_spray_output(json_file, excel_file, txt_file):
    log(f"开始处理spray结果: {json_file}")
    result = subprocess.run(
        ["python", "process_data.py", json_file, excel_file],
        capture_output=True,
        text=True
    )
    if result.stdout:
        for line in result.stdout.splitlines():
            log(f"process_data.py: {line}")
    if result.stderr:
        for line in result.stderr.splitlines():
            log(f"process_data.py stderr: {line}")
    if result.returncode != 0:
        log(f"警告: spray结果未生成结构化Excel，返回码 {result.returncode}")
        return False
    if not os.path.exists(excel_file):
        log(f"警告: 处理后的Excel文件未生成: {excel_file}")
        return False
    if not os.path.exists(txt_file):
        log(f"警告: 未找到URL列表文件: {txt_file}，可能没有有效URL")
        return False
    with open(txt_file, 'r', encoding='utf-8') as f:
        url_count = len([line for line in f.readlines() if line.strip()])
    log(f"成功提取 {url_count} 个URL")
    return True


def normalize_url_list(urls):
    normalized_urls = []
    seen = set()

    for url in urls:
        normalized_url = url.strip()
        if not normalized_url:
            continue
        if not normalized_url.startswith(('http://', 'https://')):
            normalized_url = f"http://{normalized_url}"
        if normalized_url in seen:
            continue
        seen.add(normalized_url)
        normalized_urls.append(normalized_url)

    return normalized_urls


def fallback_to_input_urls(output_dir):
    if not os.path.exists(URL_FILE):
        log(f"错误: 无法回退，原始URL文件不存在: {URL_FILE}")
        return None

    with open(URL_FILE, 'r', encoding='utf-8') as f:
        urls = normalize_url_list([line for line in f if line.strip()])

    if not urls:
        log(f"错误: 无法回退，原始URL文件为空: {URL_FILE}")
        return None

    date_str = datetime.datetime.now().strftime("%Y%m%d")
    fallback_base = f"{date_str}_input_urls_fallback"
    fallback_path = generate_unique_filename(output_dir, fallback_base, ".txt")
    with open(fallback_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(urls))
    log(f"已回退使用输入URL列表: {fallback_path}，共 {len(urls)} 个URL")
    return fallback_path


def ensure_ehole_input_urls(input_file, output_dir):
    if not os.path.exists(input_file):
        log(f"错误: ehole输入文件不存在: {input_file}")
        return None

    with open(input_file, 'r', encoding='utf-8') as f:
        urls = normalize_url_list([line for line in f if line.strip()])

    if not urls:
        log(f"错误: ehole输入URL为空: {input_file}")
        return None

    date_str = datetime.datetime.now().strftime("%Y%m%d")
    normalized_base = f"{date_str}_ehole_input_urls"
    normalized_path = generate_unique_filename(output_dir, normalized_base, ".txt")
    with open(normalized_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(urls))
    log(f"已规范化ehole输入URL: {normalized_path}，共 {len(urls)} 个URL")
    return normalized_path

def filter_status_200(excel_file, output_dir, count):
    try:
        log(f"开始从 {excel_file} 中筛选状态码为200的URL...")
        if not os.path.exists(excel_file):
            log(f"错误: Excel文件不存在: {excel_file}")
            return None
        
        df = pd.read_excel(excel_file)
        if df.empty:
            log("错误: Excel文件为空")
            return None
        
        # 标记状态码列位置（J列）
        log(f"注意: Spray扫描的状态码结果配置为J列，对应Python索引 {STATUS_CODE_COL_INDEX}")
        
        try:
            status_code_col = df.columns[STATUS_CODE_COL_INDEX]
            url_col = df.columns[URL_COL_INDEX]
        except IndexError:
            log(f"错误: Excel文件列数不足，无法获取索引为 {STATUS_CODE_COL_INDEX} (J列) 或 {URL_COL_INDEX} 的列")
            log(f"Excel实际列数: {len(df.columns)}，列名: {list(df.columns)}")
            return None
        
        log(f"使用列 '{url_col}' (E列) 作为URL列，列 '{status_code_col}' (J列) 作为状态码列")
        
        if df[status_code_col].dtype not in [int, float]:
            log(f"警告: 状态码列数据类型不是数值类型: {df[status_code_col].dtype}")
            log(f"尝试转换数据类型...")
            try:
                df[status_code_col] = pd.to_numeric(df[status_code_col], errors='coerce')
            except:
                log(f"错误: 无法将状态码列转换为数值类型")
                return None
        
        df_200 = df[df[status_code_col] == 200].copy()
        total_rows = len(df)
        filtered_rows = len(df_200)
        log(f"Excel总行数: {total_rows}，状态码为200的行数: {filtered_rows}")
        
        if filtered_rows == 0:
            log("警告: 未找到状态码为200的URL")
            return None
        
        urls_200 = df_200[df.columns[URL_COL_INDEX]].dropna().unique().tolist()
        log(f"提取并去重后得到 {len(urls_200)} 个状态码为200的URL")
        
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        base_filename = f"{date_str}_status200_urls_{count}"
        
        # 使用新函数生成唯一文件名
        output_file = generate_unique_filename(output_dir, base_filename, ".txt")
        
        log(f"将状态码为200的URL写入文件: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(urls_200))
        
        with open(output_file, 'r', encoding='utf-8') as f:
            written_urls = f.read().splitlines()
        
        if len(written_urls) != len(urls_200):
            log(f"警告: 写入的URL数量({len(written_urls)})与筛选的URL数量({len(urls_200)})不一致")
        
        log(f"状态码为200的URL已保存至: {output_file}")
        return output_file
    except Exception as e:
        log(f"筛选错误: {e}")
        return None

def main():
    try:
        import psutil
        import pandas as pd

        date_folder = datetime.datetime.now().strftime("%m%d")
        full_date_dir = os.path.join(BASE_DIR, date_folder)
        os.makedirs(full_date_dir, exist_ok=True)
        setup_script_logging(full_date_dir)
        hide_python_console()
        log(f"开始自动化漏洞扫描和指纹识别流程")
        log(f"基础目录: {BASE_DIR}")
        log(f"创建日期文件夹: {full_date_dir}")
        
        # 清理指定的过程文件
        clean_process_files()
        
        # 步骤1: 执行spray扫描
        log("步骤1: 执行spray扫描...")
        spray_cmd = ["spray.exe", "-l", URL_FILE, "-d", DIR_FILE, "-f", JSON_FILE]
        spray_process = run_native_command(spray_cmd, "spray.exe")
        if not monitor_process(spray_process, "spray.exe", timeout=1800):
            log("错误: spray执行失败或超时")
            sys.exit(1)
        if not wait_for_file(JSON_FILE):
            log("错误: spray未生成结果文件")
            sys.exit(1)
        
        # 步骤2: 处理spray结果，提取有效URL
        log("步骤2: 处理spray结果，提取有效URL...")
        
        # 为输出文件生成唯一文件名
        unique_excel_file = generate_unique_filename(BASE_DIR, "res_processed", ".xlsx")
        unique_txt_file = generate_unique_filename(BASE_DIR, "res_processed", ".txt")
        
        spray_processed = process_spray_output(JSON_FILE, unique_excel_file, unique_txt_file)

        # 步骤3: 筛选状态码200的URL
        log("步骤3: 准备ehole输入URL...")
        filtered_txt_path = None
        if spray_processed:
            filtered_txt_path = filter_status_200(unique_excel_file, full_date_dir, 1)
            if not filtered_txt_path:
                log("警告: 未筛选出状态码200的URL，回退使用原始输入URL")
                filtered_txt_path = fallback_to_input_urls(full_date_dir)
        else:
            log("警告: spray输出无法结构化处理，回退使用原始输入URL")
            filtered_txt_path = fallback_to_input_urls(full_date_dir)

        if not filtered_txt_path:
            log("错误: 未生成可供ehole使用的URL文件")
            sys.exit(1)

        normalized_ehole_input = ensure_ehole_input_urls(filtered_txt_path, full_date_dir)
        if not normalized_ehole_input:
            log("错误: 未生成有效的ehole输入URL文件")
            sys.exit(1)

        # 步骤3.5: 移动Spray结果文件到日期文件夹
        log("步骤3.5: 移动Spray结果文件到日期文件夹...")

        # 为移动的文件生成唯一文件名
        spray_json_base = f"spray_original_{datetime.datetime.now().strftime('%Y%m%d')}"
        spray_json_dest = generate_unique_filename(full_date_dir, spray_json_base, ".json")

        shutil.move(JSON_FILE, spray_json_dest)
        log(f"已移动Spray原始结果: {spray_json_dest}")

        if spray_processed and os.path.exists(unique_excel_file):
            spray_excel_base = f"spray_processed_{datetime.datetime.now().strftime('%Y%m%d')}"
            spray_excel_dest = generate_unique_filename(full_date_dir, spray_excel_base, ".xlsx")
            shutil.move(unique_excel_file, spray_excel_dest)
            log(f"已移动Spray处理后Excel: {spray_excel_dest}")

        # 步骤4: 执行ehole指纹识别
        log("步骤4: 执行ehole指纹识别...")

        # 为ehole结果生成唯一文件名
        ehole_base = f"ehole_result_{datetime.datetime.now().strftime('%Y%m%d')}"
        ehole_output = generate_unique_filename(full_date_dir, ehole_base, ".xlsx")

        ehole_cmd = ["ehole", "finger", "-l", normalized_ehole_input, "-o", ehole_output, "-t", "10"]
        ehole_process = run_native_command(ehole_cmd, "ehole.exe")

        # 监控ehole进程并等待结束
        if not monitor_process(ehole_process, "ehole.exe", timeout=1800):
            log("错误: ehole执行失败或超时")
            # 即使监控失败，也继续检查文件是否存在
            pass
        
        # 检查ehole结果文件是否生成
        if not wait_for_file(ehole_output):
            log("错误: ehole未生成结果文件")
            sys.exit(1)
        
        # 美化ehole结果表格
        log("美化ehole结果表格...")
        result = subprocess.run(
            ["python", "process_data.py", ehole_output, ehole_output, normalized_ehole_input],
            capture_output=True,
            text=True
        )
        if result.stdout:
            for line in result.stdout.splitlines():
                log(f"process_data.py: {line}")
        if result.stderr:
            for line in result.stderr.splitlines():
                log(f"process_data.py stderr: {line}")
        if result.returncode != 0:
            log(f"错误: ehole结果表格美化失败，返回码 {result.returncode}")
            sys.exit(1)
        log("ehole结果表格美化完成")
        
        log(f"自动化流程全部完成！所有结果保存在: {full_date_dir}")
    
    except Exception as e:
        log(f"程序异常: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    os.system("chcp 65001 >nul 2>&1")  # 确保中文显示正常

    try:
        main()
    finally:
        teardown_script_logging()