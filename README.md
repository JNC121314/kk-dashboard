# 开开华彩数据看板·云端自动更新

每天北京时间 9:00 自动提取13个看板数据并生成HTML报告，部署到 GitHub Pages。

## 文件结构

```
├── fetch_data.py              # 数据提取脚本（从API拉取13个看板数据）
├── generate_report.py         # 报告生成脚本（v6格式）
├── data/                      # 数据文件目录（运行时生成，不提交）
├── .github/workflows/
│   └── daily-update.yml       # GitHub Actions 定时任务
└── .gitignore
```

## 首次配置步骤

### 1. 创建 GitHub 仓库

在 GitHub 上创建一个 **Private** 仓库（推荐私有，保护数据）。

### 2. 推送代码

```bash
cd kk-cloud
git init
git add .
git commit -m "云端数据看板初始化"
git branch -M main
git remote add origin git@github.com:<你的用户名>/<仓库名>.git
git push -u origin main
```

### 3. 配置 Secrets

在仓库 Settings → Secrets and variables → Actions → New repository secret：

- **Name**: `ACCOUNTS_JSON`
- **Value**:（复制以下JSON，注意是一行）

```json
[{"label":"华彩课包面板","username":"LZXQA","password":"KKHC1234"},{"label":"通用声乐面板","username":"ZHSYY","password":"kkhc1234"},{"label":"通用钢琴面板","username":"ZHGQOY","password":"kkhc1234"},{"label":"茉茉","username":"mmlGQ","password":"KKHC1234"},{"label":"郑老师/张老师","username":"ZHzlsg","password":"KKHC1234"},{"label":"黄老师","username":"Hlsgq","password":"KKHC1234"},{"label":"严老师钢琴","username":"LUYAN","password":"KKHC123L"},{"label":"莉莉辛辛","username":"Xllgq","password":"KKHC1234"},{"label":"娜娜","username":"NANA","password":"KKHC2345"},{"label":"毛毛矩阵开开慧弹琴","username":"htqgq","password":"KKHC1234"},{"label":"源源老师看板","username":"yylsgq","password":"KKHC1234"},{"label":"常老师西西","username":"ZHcsns","password":"KKHC1234"},{"label":"千千老师","username":"xzmbgq","password":"KKHC1234"}]
```

### 4. 启用 GitHub Pages

在仓库 Settings → Pages → Source 选择 `gh-pages` 分支，目录选 `/ (root)`。

首次手动触发 Actions 后，Pages 会自动生成链接：
`https://<你的用户名>.github.io/<仓库名>/`

### 5. 手动触发测试

在仓库 Actions 页面 → "每日更新数据看板" → Run workflow → 点击运行。

## 运行机制

- **定时触发**: 每天 UTC 1:00（北京时间 9:00）
- **手动触发**: Actions 页面点 Run workflow
- **流程**: 提取数据 → 生成报告 → 部署到 gh-pages 分支 → GitHub Pages 自动发布
- **不依赖本地**: 完全在 GitHub 云端运行，电脑开关机不影响
