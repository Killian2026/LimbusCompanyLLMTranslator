"""LCLT 启动器 - GUI 模式（用于 EXE 打包）"""
import os
import sys
import threading
import webbrowser
import time


def main():
    app_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_dir)

    port = 8501
    url = f"http://localhost:{port}"

    # 通过 Streamlit 内部 API 启动，避免子进程递归
    def run_streamlit():
        import streamlit.web.bootstrap
        from streamlit import config as _config

        _config.set_option("server.port", port)
        _config.set_option("server.headless", True)
        _config.set_option("browser.serverAddress", "localhost")
        _config.set_option("browser.gatherUsageStats", False)
        _config.set_option("server.enableCORS", False)
        _config.set_option("server.enableXsrfProtection", False)

        streamlit.web.bootstrap.run(
            os.path.join(app_dir, "app.py"),
            is_hello=False,
            args=[],
            flag_options={},
        )

    thread = threading.Thread(target=run_streamlit, daemon=True)
    thread.start()

    # 等待服务启动
    time.sleep(3)

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
