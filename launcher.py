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

    # 在后台线程打开浏览器（等服务器就绪）
    def open_browser():
        time.sleep(3)
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()

    print(f"LCLT 翻译工具已启动")
    print(f"请在浏览器中访问: {url}")

    # 必须在主线程运行 Streamlit（signal 模块要求）
    import streamlit.web.bootstrap
    from streamlit import config as _config

    _config.set_option("server.port", port)
    _config.set_option("server.headless", True)
    _config.set_option("browser.serverAddress", "localhost")
    _config.set_option("browser.gatherUsageStats", False)
    _config.set_option("server.enableXsrfProtection", False)

    streamlit.web.bootstrap.run(
        os.path.join(app_dir, "app.py"),
        is_hello=False,
        args=[],
        flag_options={},
    )


if __name__ == "__main__":
    main()
