"""LCLT 启动器 - GUI 模式（用于 EXE 打包）"""
import os
import sys
import threading
import webbrowser
import time


def main():
    if getattr(sys, 'frozen', False):
        app_dir = sys._MEIPASS
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_dir)

    port = 8501
    url = f"http://localhost:{port}"

    # 在后台线程打开浏览器（等服务器就绪）
    def open_browser():
        time.sleep(3)
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()

    app_path = os.path.join(app_dir, "app.py")

    print(f"LCLT 翻译工具已启动")
    print(f"请在浏览器中访问: {url}")

    sys.argv = [
        "streamlit", "run", app_path,
        "--server.port", str(port),
        "--server.headless", "true",
        "--server.enableXsrfProtection", "false",
        "--browser.gatherUsageStats", "false",
        "--browser.serverAddress", "localhost",
        "--global.developmentMode", "false",
    ]
    import streamlit.web.cli
    streamlit.web.cli.main()


if __name__ == "__main__":
    main()
