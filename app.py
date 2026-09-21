from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DRAFTS = ROOT / "drafts"


def load_env(path: Path = ROOT / ".env.local") -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def read_context() -> str:
    profile = (ROOT / "profile.md").read_text(encoding="utf-8")
    feedback = (ROOT / "feedback.md").read_text(encoding="utf-8")
    return f"创作人格：\n{profile}\n\n历史修改偏好：\n{feedback}"


def safe_draft(path: str) -> Path:
    target = Path(path).expanduser().resolve()
    if target != DRAFTS and DRAFTS not in target.parents:
        raise ValueError("只能修改 drafts/ 目录中的文章")
    if not target.is_file():
        raise ValueError(f"草稿不存在：{target}")
    return target


def save_markdown(kind: str, text: str) -> Path:
    folder = DRAFTS / datetime.now().strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{datetime.now().strftime('%H%M%S')}-{kind}.md"
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path


def remember(feedback: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d")
    with (ROOT / "feedback.md").open("a", encoding="utf-8") as file:
        file.write(f"\n- {stamp}: {feedback.strip()}\n")


def api_error_message(error: Exception) -> str | None:
    code = getattr(error, "code", None)
    if code in {"insufficient_quota", "credit_balance_exhausted"}:
        return (
            "OpenAI API 项目没有可用额度。请前往 "
            "https://platform.openai.com/settings/organization/billing 添加额度后重试。"
        )
    if code == "rate_limit_exceeded":
        return "OpenAI API 暂时达到速率限制，请稍后重试。"
    if code in {"invalid_api_key", "authentication_error"}:
        return "OpenAI API 密钥无效或无权访问当前项目。"
    return None


def build_agent():
    from agents import Agent, WebSearchTool

    model = os.getenv("OPENAI_MODEL", "").strip()
    if not model:
        raise RuntimeError("缺少 OPENAI_MODEL；选定模型后请在 .env.local 中配置")
    return Agent(
        name="视角主编",
        model=model,
        instructions="""
你是一位有人类主编把关的观点编辑 Agent。你的任务不是追逐流量或故意唱反调，
而是从心理学、社会心理、行为科学和日常经验中寻找不常见但站得住的观察角度。

规则：
1. 搜索热点时优先近期原始报道、研究机构、论文或当事方来源，并给出可访问链接。
2. 清楚区分事实、研究结论、解释和个人观点；不知道就说不知道。
3. 不诊断个人，不提供医疗建议，不用心理学概念给群体贴标签。
4. 独特不等于反对主流；必须呈现反例、局限或可能被误解之处。
5. 禁止 AI 套话、空洞金句、夸张标题和制造焦虑。
6. 永远输出 Markdown。没有人类明确确认时，只能生成候选选题或草稿，不能声称已发布。
""".strip(),
        tools=[WebSearchTool(search_context_size="high", external_web_access=True)],
    )


async def run_agent(task: str) -> str:
    from agents import Runner

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("缺少 OPENAI_API_KEY；请在 .env.local 中配置")
    result = await Runner.run(build_agent(), f"{read_context()}\n\n本次任务：\n{task}")
    return str(result.final_output)


async def discover(count: int) -> Path:
    task = f"""
搜索过去 48 小时中文和英文公共网络中的热点，筛选 {count} 个适合讨论生活、关系、工作、
自我认识或社会心理的选题。不要直接写文章。每个选题必须包含：热点概述、主流叙事、
三个不同视角、推荐视角、为什么值得谈、可能伤害或误导读者的风险、2-4 个来源链接。
最后给出编号，等待人类主编选择。
"""
    return save_markdown("topics", await run_agent(task))


async def write(topic: str, notes: str) -> Path:
    task = f"""
人类主编已经确认这个选题或视角：{topic}
补充意见：{notes or '无'}

先核查相关事实和来源，再生成一个内容包：
1. 核心观点与论证边界；
2. 小红书中文稿（标题、正文、3-5 个克制标签），严格放在
   <!-- XHS_START --> 与 <!-- XHS_END --> 之间；
3. Twitter/X 英文 thread（最多 6 条，每条不超过 280 字符），严格放在
   <!-- X_START --> 与 <!-- X_END --> 之间；多条帖子用单独一行
   ---THREAD--- 分隔；
4. 事实来源；
5. 发布前仍需人类确认的风险。
不要声称已经发布。
"""
    return save_markdown("article", await run_agent(task))


async def revise(path: str, feedback: str) -> Path:
    source = safe_draft(path)
    task = f"""
请根据人类主编反馈修改下面的草稿。保留可靠来源；若反馈与事实冲突，指出冲突而不是迎合。
必须保留 XHS_START/XHS_END、X_START/X_END 和 THREAD 分隔标记，供发布模块读取。

反馈：{feedback}

原稿：
{source.read_text(encoding='utf-8')}
"""
    output = save_markdown("revision", await run_agent(task))
    remember(feedback)
    return output


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description="有人类把关的观点编辑 Agent")
    commands = cli.add_subparsers(dest="command", required=True)
    find = commands.add_parser("discover", help="发现热点并生成候选观点卡")
    find.add_argument("--count", type=int, default=5)
    draft = commands.add_parser("write", help="根据已确认的角度写文章")
    draft.add_argument("--topic", required=True)
    draft.add_argument("--notes", default="")
    edit = commands.add_parser("revise", help="根据反馈修改草稿并记住偏好")
    edit.add_argument("file")
    edit.add_argument("--feedback", required=True)
    publish = commands.add_parser("publish", help="预览或发布已审核的 X 内容")
    publish.add_argument("file")
    publish.add_argument("--confirm", default="", help="实际发布时填写 PUBLISH")
    return cli


async def dispatch(args: argparse.Namespace) -> Path:
    if args.command == "discover":
        return await discover(args.count)
    if args.command == "write":
        return await write(args.topic, args.notes)
    if args.command == "revise":
        return await revise(args.file, args.feedback)

    from publisher import extract_x_posts, publish_x_thread

    source = safe_draft(args.file)
    posts = extract_x_posts(source.read_text(encoding="utf-8"))
    if args.confirm != "PUBLISH":
        print("\n\n--- 下一条 ---\n\n".join(posts))
        raise SystemExit("以上仅为预览；确认无误后添加 --confirm PUBLISH")
    token = os.getenv("X_USER_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("缺少 X_USER_ACCESS_TOKEN；请在 .env.local 中配置")
    ids = await asyncio.to_thread(publish_x_thread, posts, token)
    return save_markdown(
        "published-x",
        "# X 发布记录\n\n"
        + f"来源：`{source.relative_to(ROOT)}`\n\n"
        + "\n".join(f"- https://x.com/i/web/status/{post_id}" for post_id in ids),
    )


def main() -> None:
    load_env()
    args = parser().parse_args()
    try:
        output = asyncio.run(dispatch(args))
    except (RuntimeError, ValueError) as error:
        raise SystemExit(str(error)) from error
    except Exception as error:
        message = api_error_message(error)
        if message:
            raise SystemExit(message) from error
        raise
    print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
