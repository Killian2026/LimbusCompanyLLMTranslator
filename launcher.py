"""LCLT 启动器 - GUI 模式（用于 EXE 打包）"""
import os
import sys
import subprocess
import threading
import webbrowser
import time


def main():
    app_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_dir)

    port = 8501
    url = f"http://localhost:{port}"

    # 在新线程中启动 Streamlit 服务器
    def run_streamlit():
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "app.py",
             "--server.port", str(port),
             "--server.headless", "true",
             "--server.enableCORS", "false",
             "--server.enableXsrfProtection", "false",
             "--browser.serverAddress", "localhost",
             "--browser.gatherUsageStats", "false"],
            cwd=app_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    thread = threading.Thread(target=run_streamlit, daemon=True)
    thread.start()

    # 等待服务启动
    time.sleep(2)

    # 打开浏览器
    print(f"LCLT 翻译工具已启动")
    print(f"请在浏览器中访问: {url}")
    webbrowser.open(url)

    # 保持进程运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("退出")


if __name__ == "__main__":
    main()
