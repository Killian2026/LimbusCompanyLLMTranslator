"""
LCLT GUI - Streamlit 前端
"""
import streamlit as st
import json
import os
import sys
import time
import threading
import copy
import glob as glob_module

st.set_page_config(
    page_title="LCLT 边狱巴士翻译工具",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from src.main import LCLT
from src.config.loader import config_loader

# ============================================================
# 游戏目录自动检测
# ============================================================

GAME_MARKER = "LimbusCompany_Data/Assets/Resources_moved/Localize/jp"
STEAM_COMMON_DIRS = [
    "C:/Program Files (x86)/Steam/steamapps/common",
    "D:/Steam/steamapps/common",
    "E:/Steam/steamapps/common",
    "F:/Steam/steamapps/common",
    "G:/Steam/steamapps/common",
]


def _find_game_in_common(common_dir):
    game_dir = os.path.join(common_dir, "Limbus Company")
    if os.path.isdir(os.path.join(game_dir, GAME_MARKER)):
        return game_dir
    return None


def _read_steam_libraries():
    """从 Steam libraryfolders.vdf 中读取所有库路径"""
    libraries = []
    for steam_root in ["C:/Program Files (x86)/Steam", "D:/Steam", "E:/Steam", "F:/Steam", "G:/Steam"]:
        vdf = os.path.join(steam_root, "steamapps", "libraryfolders.vdf")
        if not os.path.isfile(vdf):
            continue
        try:
            with open(vdf, "r", encoding="utf-8") as f:
                for line in f:
                    # libraryfolders.vdf: "path"  "D:\\SteamLibrary"
                    if '"path"' in line:
                        path = line.split('"')[3].replace("\\\\", "/")
                        lib_common = os.path.join(path, "steamapps", "common")
                        if os.path.isdir(lib_common):
                            libraries.append(lib_common)
        except Exception:
            pass
    return libraries


def detect_game_directory():
    """自动搜索 Limbus Company 安装目录，返回路径或 None"""
    all_common = list(STEAM_COMMON_DIRS)

    for lib in _read_steam_libraries():
        if lib not in all_common:
            all_common.append(lib)

    for common_dir in all_common:
        result = _find_game_in_common(common_dir)
        if result:
            return result

    # 最后手段：直接搜索根目录
    for drive in ["C:/", "D:/", "E:/", "F:/"]:
        candidate = os.path.join(drive, "Limbus Company")
        if os.path.isdir(os.path.join(candidate, GAME_MARKER)):
            return candidate

    return None


def _save_setup_progress():
    """保存已完成的配置步骤（游戏路径 + API）"""
    cfg = load_config()

    # 保存游戏路径
    if st.session_state.get("use_detected_path"):
        cfg["file_paths"]["input_direction"] = st.session_state.detected_input
        cfg["file_paths"]["output_direction"] = st.session_state.detected_output
    elif st.session_state.get("detected_input"):
        cfg["file_paths"]["input_direction"] = st.session_state.detected_input
        cfg["file_paths"]["output_direction"] = st.session_state.detected_output
    save_config(cfg)

    # 保存 API 配置
    url = st.session_state.get("temp_api_url", "")
    key = st.session_state.get("temp_api_key", "")
    if url or key:
        models = load_models()
        main_model = models["models"].get("main", {})
        main_model["base_url"] = url
        if key:
            main_model["api_key"] = key
        save_models(models)


def is_first_launch():
    """检查是否首次启动（游戏路径未配置）"""
    try:
        cfg = load_config()
        inp = cfg.get("file_paths", {}).get("input_direction", "")
        if not inp or "<" in str(inp):
            return True
        return False
    except Exception:
        return True


# ============================================================
# 数据加载 / 保存
# ============================================================

def load_config():
    with open(os.path.join(BASE_DIR, "config.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg):
    with open(os.path.join(BASE_DIR, "config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    config_loader._config_cache = None


def load_models():
    with open(os.path.join(BASE_DIR, "models.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def save_models(m):
    with open(os.path.join(BASE_DIR, "models.json"), "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
    config_loader._models_cache = None


def load_strategies():
    with open(os.path.join(BASE_DIR, "translation_configs.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def save_strategies(s):
    with open(os.path.join(BASE_DIR, "translation_configs.json"), "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    config_loader._translation_configs_cache = None

# ============================================================
# Sidebar
# ============================================================

# ============================================================
# 首次启动向导
# ============================================================

if "setup_done" not in st.session_state:
    st.session_state.setup_done = not is_first_launch()
if "setup_step" not in st.session_state:
    st.session_state.setup_step = 1

if not st.session_state.setup_done:
    st.title("👋 欢迎使用 LCLT")

    # ---- 步骤指示器 ----
    step_labels = {1: "📂 游戏目录", 2: "🔑 API 配置", 3: "🔤 字体配置"}
    steps_html = ""
    for s in (1, 2, 3):
        if s == st.session_state.setup_step:
            steps_html += f"<span style='background:#ff4b4b;color:#fff;padding:6px 16px;border-radius:6px;margin:4px;font-weight:bold'>{step_labels[s]}</span>"
        elif s < st.session_state.setup_step:
            steps_html += f"<span style='background:#4caf50;color:#fff;padding:6px 16px;border-radius:6px;margin:4px'>✅ {step_labels[s]}</span>"
        else:
            steps_html += f"<span style='background:#444;color:#aaa;padding:6px 16px;border-radius:6px;margin:4px'>{step_labels[s]}</span>"
        if s < 3:
            steps_html += " → "
    st.markdown(steps_html, unsafe_allow_html=True)
    st.divider()

    # ============================================================
    # 第一步：游戏目录
    # ============================================================
    if st.session_state.setup_step == 1:
        st.subheader("📂 选择游戏目录")
        st.caption("Limbus Company 的安装位置，用于读取原文和输出翻译")

        if "use_detected_path" not in st.session_state:
            st.session_state.use_detected_path = False

        detected = detect_game_directory()

        if detected:
            input_dir = os.path.join(detected, GAME_MARKER.rsplit("/", 1)[0]).replace("\\", "/")
            output_dir = os.path.join(detected, "LimbusCompany_Data", "Lang").replace("\\", "/")
            st.success(f"✅ 自动检测到：`{detected}`")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ 使用自动检测的目录", type="primary", use_container_width=True):
                    st.session_state.use_detected_path = True
                    st.session_state.detected_input = input_dir
                    st.session_state.detected_output = output_dir
                    st.session_state.setup_step = 2
                    st.rerun()
            with c2:
                if st.button("📂 手动指定", use_container_width=True):
                    st.session_state.show_game_manual = True
                    st.rerun()
        else:
            st.warning("未能自动检测到游戏目录，请手动输入")
            st.session_state.show_game_manual = True

        if st.session_state.get("show_game_manual"):
            manual_in = st.text_input(
                "原文目录 (Localize 的上级目录)",
                placeholder="C:/.../LimbusCompany_Data/Assets/Resources_moved/Localize",
                key="setup_game_in"
            )
            manual_out = st.text_input(
                "输出目录 (Lang 的上级目录)",
                placeholder="C:/.../LimbusCompany_Data/Lang",
                key="setup_game_out"
            )

        # 底部按钮
        st.divider()
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("⏭️ 稍后配置", use_container_width=True):
                st.session_state.setup_step = 2
                st.rerun()
        with col3:
            manual_ok = st.session_state.get("show_game_manual") and st.session_state.get("setup_game_in", "").strip()
            if manual_ok:
                if st.button("下一步 ➡️", type="primary", use_container_width=True):
                    st.session_state.use_detected_path = False
                    st.session_state.detected_input = st.session_state.get("setup_game_in", "").strip().replace("\\", "/")
                    st.session_state.detected_output = st.session_state.get("setup_game_out", "").strip().replace("\\", "/")
                    st.session_state.setup_step = 2
                    st.rerun()

    # ============================================================
    # 第二步：API 配置
    # ============================================================
    elif st.session_state.setup_step == 2:
        st.subheader("🔑 API 配置")
        st.caption("使用 OpenAI 兼容接口，支持 DeepSeek、OpenAI 等")

        models = load_models()
        main_model = models["models"].get("main", {})

        api_url = st.text_input(
            "API Base URL",
            value=main_model.get("base_url", "https://api.deepseek.com/chat/completions"),
            key="setup_api_url",
            placeholder="https://api.deepseek.com/chat/completions"
        )
        api_key = st.text_input(
            "API Key",
            value=main_model.get("api_key", ""),
            type="password",
            key="setup_api_key",
            placeholder="sk-..."
        )

        # 底部按钮
        st.divider()
        col_back, col_skip, col_next = st.columns([1, 1, 1])
        with col_back:
            if st.button("⬅️ 上一步", use_container_width=True):
                st.session_state.setup_step = 1
                st.rerun()
        with col_skip:
            if st.button("⏭️ 稍后配置", use_container_width=True):
                st.session_state.setup_step = 3
                st.rerun()
        with col_next:
            if st.button("下一步 ➡️", type="primary", use_container_width=True):
                st.session_state.temp_api_url = api_url.strip()
                st.session_state.temp_api_key = api_key.strip()
                st.session_state.setup_step = 3
                st.rerun()

    # ============================================================
    # 第三步：字体配置
    # ============================================================
    elif st.session_state.setup_step == 3:
        st.subheader("🔤 字体配置")
        st.caption("翻译后的文本需要字体才能正确显示")

        st.markdown("""
        **如果你希望从头翻译**（游戏尚未被翻译过）：
        - 需要在 `Font/Context/` 文件夹中放入 `.ttf` 字体文件
        - `Font/Title/` 为可选，用于标题字体

        **如果你已有字体文件夹**（如在零协会等已有翻译的基础上再次翻译）：
        - 字体已经就位，可直接跳过此步骤
        """)

        # ---- Context 字体 ----
        context_dir = os.path.join(BASE_DIR, "Font", "Context")
        os.makedirs(context_dir, exist_ok=True)
        context_fonts = glob_module.glob(os.path.join(context_dir, "*.ttf"))

        st.markdown("##### 📄 Context 字体（必需）")
        if context_fonts:
            st.success(f"✅ 已配置：`{os.path.basename(context_fonts[0])}`")
        else:
            st.warning("⚠️ 未检测到字体文件")
            ctx_font = st.file_uploader(
                "上传 Context 字体 (.ttf)",
                type=["ttf"],
                key="setup_font_context",
                help="选择 .ttf 字体文件，将复制到 Font/Context/ 目录"
            )
            if ctx_font:
                font_path = os.path.join(context_dir, ctx_font.name)
                with open(font_path, "wb") as f:
                    f.write(ctx_font.read())
                st.success(f"✅ `{ctx_font.name}` 已复制到 Font/Context/")
                st.rerun()

        # ---- Title 字体 ----
        st.markdown("##### 📝 Title 字体（可选）")
        title_dir = os.path.join(BASE_DIR, "Font", "Title")
        # 只有上传了 Title 字体才创建目录
        title_fonts = glob_module.glob(os.path.join(title_dir, "*.ttf")) if os.path.isdir(title_dir) else []

        if title_fonts:
            st.success(f"✅ 已配置：`{os.path.basename(title_fonts[0])}`")
        else:
            st.caption("可以不填，不会创建 Title 字体目录")
            title_font = st.file_uploader(
                "上传 Title 字体 (.ttf)",
                type=["ttf"],
                key="setup_font_title",
                help="可选，选择 .ttf 标题字体，将复制到 Font/Title/ 目录"
            )
            if title_font:
                os.makedirs(title_dir, exist_ok=True)
                font_path = os.path.join(title_dir, title_font.name)
                with open(font_path, "wb") as f:
                    f.write(title_font.read())
                st.success(f"✅ `{title_font.name}` 已复制到 Font/Title/")
                st.rerun()

        # 底部按钮
        st.divider()
        col_back, col_skip, col_done = st.columns([1, 1, 1])
        with col_back:
            if st.button("⬅️ 上一步", use_container_width=True):
                st.session_state.setup_step = 2
                st.rerun()
        with col_skip:
            if st.button("⏭️ 稍后配置", use_container_width=True):
                _save_setup_progress()
                st.session_state.setup_done = True
                st.rerun()
        with col_done:
            if st.button("🚀 开始使用", type="primary", use_container_width=True):
                _save_setup_progress()
                st.session_state.setup_done = True
                st.rerun()

    st.stop()

# ============================================================
# Sidebar
# ============================================================

st.sidebar.title("LCLT 🚌")
st.sidebar.markdown("边狱巴士 LLM 翻译工具")
page = st.sidebar.radio("页面", ["⚙️ 配置", "🧩 模型管理", "📝 翻译策略", "🌐 翻译", "📋 关于"])

# ============================================================
# 配置页
# ============================================================
if page == "⚙️ 配置":
    st.header("翻译设置")

    cfg = load_config()
    ts = cfg["translation_settings"]

    col1, col2, col3 = st.columns(3)
    with col1:
        ts["origin_language"] = st.text_input("源语言", value=ts["origin_language"])
        ts["max_workers"] = st.number_input("最大线程数", min_value=1, max_value=2000, value=ts["max_workers"])
    with col2:
        ts["target_direction"] = st.text_input("目标语言目录", value=ts["target_direction"])
        ts["max_chars_per_batch"] = st.number_input("每批字符上限", min_value=100, max_value=50000, value=ts["max_chars_per_batch"])
    with col3:
        ts["max_retries"] = st.number_input("API 重试次数", min_value=0, max_value=10, value=ts["max_retries"])
        ts["timeout"] = st.number_input("API 超时 (秒)", min_value=10, max_value=600, value=ts["timeout"])

    st.divider()
    st.subheader("文件路径")
    fp = cfg["file_paths"]
    fp["input_direction"] = st.text_input("游戏原文目录", value=fp.get("input_direction", ""),
                                           help="Limbus Company 的 Localize 目录路径")
    fp["output_direction"] = st.text_input("翻译输出目录", value=fp.get("output_direction", ""),
                                            help="Limbus Company 的 Lang 目录路径")

    st.divider()
    st.subheader("选项")
    opt = cfg.setdefault("options", {})
    col1, col2 = st.columns(2)
    with col1:
        opt["keep_backup_files"] = st.checkbox("保留备份文件", value=opt.get("keep_backup_files", True))
        opt["confirm_before_translation"] = st.checkbox("翻译前确认", value=opt.get("confirm_before_translation", True))
    with col2:
        opt["generate_debug_file"] = st.checkbox("生成调试文件", value=opt.get("generate_debug_file", False))

    if st.button("💾 保存翻译设置", type="primary"):
        save_config(cfg)
        st.success("翻译设置已保存")

# ============================================================
# 模型管理页
# ============================================================
elif page == "🧩 模型管理":
    st.header("模型管理")
    st.caption("管理 models.json，名称（如 origin/story/skill）用于在翻译策略中引用")

    models = load_models()
    model_names = list(models["models"].keys())

    # ---- 添加新模型 ----
    with st.expander("➕ 添加新模型"):
        nc1, nc2 = st.columns([2, 1])
        with nc1:
            new_name = st.text_input("模型名称（小写英文）", key="new_model_name", placeholder="例如 my_model")
        with nc2:
            st.write("")
            st.write("")
            if st.button("添加", key="add_model_btn") and new_name.strip():
                clean = new_name.strip().lower()
                if clean not in models["models"]:
                    models["models"][clean] = {
                        "api_key": "",
                        "base_url": "https://api.deepseek.com/chat/completions",
                        "model": "deepseek-v4-flash",
                        "temperature": 0.1,
                        "enable_thinking": False,
                    }
                    save_models(models)
                    st.success(f"已添加 **{clean}**")
                    st.rerun()
                else:
                    st.error("该名称已存在")

    st.divider()

    # ---- 编辑 / 删除模型 ----
    for model_name in model_names:
        m = models["models"][model_name]
        with st.expander(f"📦 {model_name}"):
            c1, c2 = st.columns([2, 1])
            with c1:
                m["model"] = st.text_input("模型标识", value=m["model"], key=f"m_{model_name}")
                m["base_url"] = st.text_input("Base URL", value=m["base_url"], key=f"url_{model_name}")
                m["api_key"] = st.text_input("API Key", value=m["api_key"], type="password", key=f"key_{model_name}")
            with c2:
                m["temperature"] = st.slider("Temperature", 0.0, 2.0, float(m["temperature"]), 0.1, key=f"tmp_{model_name}")
                m["enable_thinking"] = st.checkbox("启用思考", value=m.get("enable_thinking", False), key=f"think_{model_name}")

            col_del, _, col_save = st.columns([1, 3, 1])
            with col_del:
                if st.button(f"🗑️ 删除 {model_name}", key=f"del_{model_name}"):
                    st.session_state[f"confirm_del_{model_name}"] = True
                if st.session_state.get(f"confirm_del_{model_name}"):
                    st.warning(f"确认删除 **{model_name}**？")
                    cf1, cf2 = st.columns(2)
                    with cf1:
                        if st.button("确认删除", key=f"delok_{model_name}"):
                            del models["models"][model_name]
                            save_models(models)
                            st.session_state[f"confirm_del_{model_name}"] = False
                            st.success(f"已删除 {model_name}")
                            st.rerun()
                    with cf2:
                        if st.button("取消", key=f"delno_{model_name}"):
                            st.session_state[f"confirm_del_{model_name}"] = False
                            st.rerun()
            with col_save:
                if st.button(f"💾 保存 {model_name}", key=f"save_{model_name}"):
                    save_models(models)
                    st.success(f"**{model_name}** 已保存")

# ============================================================
# 翻译策略管理页
# ============================================================
elif page == "📝 翻译策略":
    st.header("翻译策略管理")
    st.caption("管理 translation_configs.json，优先级数字越小越先匹配，999 为兜底")

    strategies_data = load_strategies()
    strategies = strategies_data.get("translation_strategies", [])
    strategies.sort(key=lambda s: s.get("priority", 999))

    prompts_dir = os.path.join(BASE_DIR, "prompts")
    terminology_dir = os.path.join(BASE_DIR, "terminology")
    available_prompts = [f"prompts/{f}" for f in os.listdir(prompts_dir) if f.endswith(".txt")] if os.path.exists(prompts_dir) else []
    available_terms = [f"terminology/{f}" for f in os.listdir(terminology_dir) if f.endswith(".json")] if os.path.exists(terminology_dir) else []

    # ---- 添加新策略 ----
    with st.expander("➕ 添加新策略"):
        nc1, nc2 = st.columns([2, 1])
        with nc1:
            new_sname = st.text_input("策略名称（小写英文）", key="new_strategy_name", placeholder="例如 my_strategy")
        with nc2:
            st.write("")
            st.write("")
            if st.button("添加", key="add_strategy_btn") and new_sname.strip():
                clean = new_sname.strip().lower()
                strategies.append({
                    "name": clean,
                    "priority": 100,
                    "file_patterns": [{"pattern": "*"}],
                    "model": "origin",
                    "prompt_file": "prompts/default_prompt.txt",
                })
                strategies_data["translation_strategies"] = strategies
                save_strategies(strategies_data)
                st.success(f"已添加 **{clean}**")
                st.rerun()

    st.divider()

    # ---- 编辑策略 ----
    for si, s in enumerate(strategies):
        pat_count = len(s.get("file_patterns", []))
        pat_sample = s.get("file_patterns", [{}])[0].get("pattern", "*")[:40]
        if pat_count > 1:
            pat_sample += f"  +{pat_count - 1} 项"

        with st.expander(f"🎯 {s.get('name', '?')}"):
            col_name, col_pri, col_model = st.columns(3)
            with col_name:
                s["name"] = st.text_input("策略名称", value=s.get("name", ""), key=f"sname_{si}")
            with col_pri:
                s["priority"] = st.number_input("优先级", min_value=1, max_value=999, value=s.get("priority", 999), key=f"spri_{si}")
            with col_model:
                s["model"] = st.text_input("引用模型", value=s.get("model", ""), key=f"smodel_{si}",
                                           help="对应模型管理中的模型名称")

            col_prompt, col_term = st.columns(2)
            with col_prompt:
                s["prompt_file"] = st.selectbox("提示词",
                    options=available_prompts + [s.get("prompt_file", "")],
                    index=(available_prompts + [s.get("prompt_file", "")]).index(s.get("prompt_file", "")) if s.get("prompt_file") in available_prompts else 0,
                    key=f"sprompt_{si}")
            with col_term:
                terms = s.get("terminology_file", "")
                term_options = ["(不启用)"] + available_terms
                if terms not in term_options and terms:
                    term_options.append(terms)
                idx = term_options.index(terms) if terms in term_options else 0
                selected_term = st.selectbox("术语库", options=term_options, index=idx, key=f"sterm_{si}")
                if selected_term == "(不启用)":
                    s.pop("terminology_file", None)
                else:
                    s["terminology_file"] = selected_term

            # ---- 文件匹配模式 ----
            st.caption("📁 文件匹配模式 (glob)")
            patterns = s.get("file_patterns", [])
            dirty = False
            for pi in range(len(patterns)):
                p = patterns[pi]
                pc1, pc2, pc3 = st.columns([4, 4, 1])
                with pc1:
                    patterns[pi]["pattern"] = st.text_input(
                        "Pattern", value=p.get("pattern", ""),
                        key=f"pat_{si}_{pi}",
                        placeholder="例如 *StoryData/* 或 *Skills*"
                    )
                with pc2:
                    ef_val = ", ".join(p.get("extract_fields", []))
                    new_ef = st.text_input(
                        "提取字段 (逗号分隔，留空=全部)",
                        value=ef_val, key=f"ef_{si}_{pi}",
                        placeholder="例如 flavor, name"
                    )
                    ef_list = [x.strip() for x in new_ef.split(",") if x.strip()]
                    patterns[pi]["extract_fields"] = ef_list if ef_list else []
                    if not patterns[pi].get("extract_fields"):
                        patterns[pi].pop("extract_fields", None)
                with pc3:
                    st.write("")
                    if st.button("✕", key=f"delpat_{si}_{pi}", help="移除此匹配"):
                        patterns.pop(pi)
                        dirty = True
                        st.rerun()

            c_add, _ = st.columns([1, 3])
            with c_add:
                if st.button("➕ 添加匹配", key=f"addpat_{si}"):
                    patterns.append({"pattern": "*"})
                    st.rerun()

            # ---- 操作 ----
            col_del, _, col_save = st.columns([1, 3, 1])
            with col_del:
                if st.button(f"🗑️ 删除策略", key=f"dels_{si}"):
                    st.session_state[f"confirm_dels_{si}"] = True
                if st.session_state.get(f"confirm_dels_{si}"):
                    st.warning(f"确认删除策略 **{s.get('name', '?')}**？")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("确认", key=f"delsok_{si}"):
                            strategies.pop(si)
                            strategies_data["translation_strategies"] = strategies
                            save_strategies(strategies_data)
                            st.session_state[f"confirm_dels_{si}"] = False
                            st.success("已删除")
                            st.rerun()
                    with c2:
                        if st.button("取消", key=f"delsno_{si}"):
                            st.session_state[f"confirm_dels_{si}"] = False
                            st.rerun()
            with col_save:
                if st.button(f"💾 保存策略", key=f"saves_{si}"):
                    strategies_data["translation_strategies"] = strategies
                    save_strategies(strategies_data)
                    st.success(f"**{s.get('name', '?')}** 已保存")

# ============================================================
# 翻译页
# ============================================================
elif page == "🌐 翻译":
    st.header("执行翻译")

    cfg = load_config()
    ts = cfg["translation_settings"]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("源语言", ts["origin_language"])
    with col2:
        st.metric("目标", ts["target_direction"])
    with col3:
        st.metric("线程数", ts["max_workers"])
    with col4:
        st.metric("每批字符", ts["max_chars_per_batch"])

    fp = cfg.get("file_paths", {})
    st.caption(f"原文: {fp.get('input_direction', '?')}")
    st.caption(f"输出: {fp.get('output_direction', '?')}")

    test_mode = st.checkbox("测试模式", value=False, help="使用 test/ 目录的少量文件进行测试")

    if st.button("🚀 开始翻译", type="primary", use_container_width=True):
        config_loader._config_cache = None
        config_loader._models_cache = None

        lclt = LCLT()
        lclt.config["options"]["confirm_before_translation"] = False

        progress_bar = st.progress(0.0)
        status_text = st.empty()
        log_area = st.empty()

        logs = []
        progress_lock = threading.Lock()
        current_progress = [0, 1]

        def add_log(msg):
            logs.append(msg)
            if len(logs) > 50:
                logs.pop(0)
            log_area.text("\n".join(logs[-30:]))

        def progress_cb(completed, total):
            with progress_lock:
                current_progress[0] = completed
                current_progress[1] = max(total, 1)

        original_method = lclt.translator.batch_translate_with_multiple_strategies

        def patched_translate(tasks, max_chars_per_batch=None, progress_callback=None, **kwargs):
            def combined_cb(completed, total):
                progress_cb(completed, total)
                if progress_callback:
                    progress_callback(completed, total)
            return original_method(tasks, max_chars_per_batch, combined_cb)

        lclt.translator.batch_translate_with_multiple_strategies = patched_translate

        def run():
            try:
                if test_mode:
                    test_dir = os.path.join(BASE_DIR, "test")
                    os.makedirs(os.path.join(test_dir, "jp"), exist_ok=True)
                    os.makedirs(os.path.join(test_dir, ts["target_direction"]), exist_ok=True)
                    lclt.config["file_paths"]["test_dir_in"] = test_dir
                    lclt.config["file_paths"]["test_dir_out"] = test_dir
                    lclt.update(test=True, log=True)
                else:
                    lclt.update()
            except Exception as e:
                add_log(f"错误: {e}")
                import traceback
                add_log(traceback.format_exc()[-500:])

        import io
        old_stdout = sys.stdout
        sys.stdout = captured = io.StringIO()

        try:
            thread = threading.Thread(target=run, daemon=True)
            thread.start()

            prev_progress = 0
            while thread.is_alive():
                thread.join(timeout=0.3)
                with progress_lock:
                    pct = current_progress[0] / max(current_progress[1], 1)
                if pct != prev_progress:
                    progress_bar.progress(min(pct, 1.0))
                    status_text.text(f"翻译中: {current_progress[0]}/{current_progress[1]}")

                captured_text = captured.getvalue()
                if captured_text and captured_text != "".join(logs):
                    for line in captured_text.split("\n"):
                        stripped = line.strip()
                        if stripped and stripped not in logs:
                            add_log(stripped)

                prev_progress = pct

            captured_text = captured.getvalue()
            for line in captured_text.split("\n"):
                stripped = line.strip()
                if stripped and stripped not in logs:
                    add_log(stripped)

            progress_bar.progress(1.0)
            status_text.text("翻译完成!")
            st.success("翻译任务已完成")

        finally:
            sys.stdout = old_stdout

# ============================================================
# 关于页
# ============================================================
else:
    st.header("关于 LCLT")
    st.markdown("""
    **LCLT** (Limbus Company LLM Translator) 是一个基于 LLM 的《边狱巴士》游戏翻译工具。

    ### 功能
    - 🔍 增量翻译 — 只翻译新增内容，节省 API 费用
    - ⚡ 多线程批量翻译 — 极快速度
    - 📚 术语库支持 — 保持专有名词一致性
    - 🎯 多策略翻译 — 不同文本类型使用不同 prompt

    ### 仓库
    [Killian2026/LimbusCompanyLLMTranslator](https://github.com/Killian2026/LimbusCompanyLLMTranslator)
    """)
