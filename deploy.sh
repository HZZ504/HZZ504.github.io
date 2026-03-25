#!/bin/bash
# 张翰之个人网站 — 一键部署到 GitHub Pages
# 使用方法: chmod +x deploy.sh && ./deploy.sh

set -e

echo "开始部署个人网站..."

# 1. 检查 git 和 gh CLI
if ! command -v git &> /dev/null; then
    echo "请先安装 git: https://git-scm.com"
    exit 1
fi
if ! command -v gh &> /dev/null; then
    echo "请先安装 GitHub CLI: https://cli.github.com"
    exit 1
fi

# 2. 检查 GitHub 登录状态
if ! gh auth status &> /dev/null; then
    echo "请先登录 GitHub..."
    gh auth login
fi

# 3. 获取 GitHub 用户名
GITHUB_USER=$(gh api user -q .login)
REPO_NAME="${GITHUB_USER}.github.io"
echo "GitHub 用户: $GITHUB_USER"
echo "仓库名称: $REPO_NAME"

# 4. 初始化 git 仓库
if [ ! -d .git ]; then
    echo "初始化 Git 仓库..."
    git init
    # 创建 .gitignore
    cat > .gitignore << 'IGNORE'
.DS_Store
node_modules/
.autoteam*
*.pyc
__pycache__/
IGNORE
fi

# 5. 提交所有文件
echo "提交文件..."
git add -A
git commit -m "Initial deploy: personal website with blog and SEO" || echo "没有新的更改需要提交"

# 6. 创建 GitHub 仓库并推送
echo "创建 GitHub 仓库..."
if gh repo view "$GITHUB_USER/$REPO_NAME" &> /dev/null; then
    echo "仓库已存在，直接推送..."
    git remote remove origin 2>/dev/null || true
    git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git"
    git branch -M main
    git push -u origin main --force
else
    gh repo create "$REPO_NAME" --public --source=. --push
fi

# 7. 启用 GitHub Pages
echo "启用 GitHub Pages..."
gh api "repos/$GITHUB_USER/$REPO_NAME/pages" -X POST \
    -f "source[branch]=main" -f "source[path]=/" 2>/dev/null || \
    echo "GitHub Pages 可能已启用"

# 8. 完成
echo ""
echo "部署完成！"
echo "你的网站地址: https://$REPO_NAME"
echo "首次部署可能需要 1-2 分钟生效"
echo ""
echo "后续更新只需运行:"
echo "  git add -A && git commit -m '更新' && git push"
