# 发布流程

## 环境准备

1. 安装依赖：`pip install pyinstaller requests tqdm`
2. 创建 [GitHub Personal Access Token](https://github.com/settings/tokens) (classic)，勾选 `repo` 权限
3. 将 token 写入项目根目录 `.gh_token` 文件（已加入 `.gitignore`，不会提交）

## 发布步骤

```bash
# 1. 提交所有代码变更
git add -A
git commit -m "xxxxx"

# 2. 一键构建 & 发布
python build_release.py --mode release --version vX.Y.Z
```

`--version` 省略时自动从 git tag 推算。

## 仅本地构建（不上传）

```bash
python build_release.py --mode local
```

产物在 `release/` 目录。

## Token 配置

两种方式，脚本按优先级读取：

1. 环境变量：`set GITHUB_TOKEN=ghp_xxxx`
2. 文件：项目根目录 `.gh_token`（推荐）
