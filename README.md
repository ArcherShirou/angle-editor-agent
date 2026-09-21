# Angle Editor Agent

一个由你担任主编的 AI 创作助手：发现热点，提出不人云亦云但有依据的心理学视角，
在你确认后生成小红书和 Twitter/X 草稿，并根据反馈持续修改。

## 工作流

1. Agent 搜索最近热点，只生成候选观点卡。
2. 你选择一个角度，并补充立场和边界。
3. Agent 核查资料，生成两个平台的草稿。
4. 你提出修改意见；意见会记录到 `feedback.md`。
5. 你人工确认并发布。首版不会自动操作社交账号。

## 安装

需要 Python 3.11+。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

本地密钥保存在被 Git 忽略的 `.env.local`：

```text
OPENAI_API_KEY=...
OPENAI_MODEL=
X_USER_ACCESS_TOKEN=
```

模型暂不预设。决定使用哪个模型后，再填写 `OPENAI_MODEL`。

## 使用

```bash
# 生成 5 个热点观点卡
angle-agent discover

# 你确认角度后生成文章
angle-agent write --topic "情绪价值正在变成关系绩效" \
  --notes "不要责怪年轻人，重点讨论自我调节被外包"

# 按反馈改稿；输出为新文件，不覆盖原稿
angle-agent revise drafts/2026-09-21/120000-article.md \
  --feedback "开头更生活化，删掉居高临下的表达"

# 先预览已审核的 X 内容，不会发布
angle-agent publish drafts/2026-09-21/120000-article.md

# 明确确认后，通过 X 官方 API 发布
angle-agent publish drafts/2026-09-21/120000-article.md --confirm PUBLISH
```

结果保存在 `drafts/YYYY-MM-DD/`。编辑 `profile.md` 可以直接调整创作人格。

## 自动发布

X 发布使用官方 `POST /2/tweets` 接口。`X_USER_ACCESS_TOKEN` 必须是包含 `tweet.write`
权限的 OAuth 2.0 用户访问令牌。未提供 `--confirm PUBLISH` 时命令只显示预览；发布成功后
会保存包含帖子链接的本地记录。

小红书稿件仍会生成在 `XHS_START/XHS_END` 标记之间，但当前不自动发布。小红书公开平台
尚未提供适用于普通创作者笔记的通用发布接口，因此项目不使用模拟点击或非官方接口。

## 内容边界

- 不做心理诊断或医疗建议。
- 心理学结论必须有可靠来源，并与个人观点分开。
- 独特观点必须呈现局限，不为了唱反调而唱反调。
- 所有内容发布前必须由人确认。

项目使用 [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents/sdk)，
由一个主编 Agent 调用网络搜索工具完成研究和写作。

如果出现“没有可用额度”，请在 [OpenAI API Billing](https://platform.openai.com/settings/organization/billing)
添加 API 额度。ChatGPT 订阅与 API 计费相互独立。

## 每日任务

GitHub Actions 每天北京时间 09:00 检查一次配置。只有仓库 Secret `OPENAI_API_KEY`
和仓库 Variable `OPENAI_MODEL` 都已设置时才会生成观点卡；当前模型留空，因此任务会安全跳过。
