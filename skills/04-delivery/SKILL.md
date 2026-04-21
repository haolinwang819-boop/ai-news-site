---
name: ai-news-delivery
description: AI资讯信息发布 Skill。负责把处理完成的日报安全地发布到邮件和网页渠道，并处理订阅、预览、调度与发送前校验。当用户提到“发送邮件”“邮件推送”“发布日报”“配置SMTP”“定时发送”“网页上线”时触发。
---

# 信息发布 Skill

This skill is only for the final delivery stage. It assumes collection and processing are already done.

Do not publish raw crawl output. Only deliver items that already passed normalization, ranking, category assignment, and dedup.
For every daily run, delivery should assume the digest already contains the mandatory English display structure: rewritten headline, summary paragraph, and three bullet takeaways.

## 发布渠道

### 渠道 1：Web 页面

通过 Vibe Coding 方式构建资讯展示网页：

- 读取 03-display 生成的 Markdown 文件
- 渲染为响应式 Web 页面
- 支持按模块/标签筛选
- 上传至服务器或静态托管平台

> Web 页面的 UI 设计与开发属于独立的前端工作，本 Skill 仅负责内容的上传部署流程。

### 渠道 2：邮件推送

通过 SMTP 将日报发送到订阅用户的邮箱。

## Pre-Send Checklist

Before sending or publishing, confirm:
- the digest is not raw source output
- every item has a valid source and link
- duplicate cross-platform items have been collapsed
- social and community items are labeled clearly
- the lead headline comes from the highest-authority item available
- reader-facing copy is in English
- final headlines are rewritten editorial headlines, not raw source-title passthrough
- every displayed item includes one summary paragraph and three bullet takeaways

## 邮件配置

### SMTP 配置

Prefer environment variables or secret storage. Do not hardcode live passwords in tracked files.

Example target config shape in `AI资讯/ai-news-aggregator/scripts/config.py`:

```python
EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "use_tls": True,
    "sender_email": "your-email@gmail.com",
    "sender_password": "your-app-password",
    "recipient_email": "recipient@example.com"
}
```

**Gmail 设置要求**：
1. 开启两步验证
2. 生成应用专用密码（Google 账号 → 安全 → 应用密码）
3. 使用应用密码而非账号密码

### 模块订阅

Users may subscribe by module and, if needed later, by source family:
- only `llm` or only `image_video`
- official-heavy digest
- broader digest including creator/community signal

## 运行方式

```bash
cd AI资讯/ai-news-aggregator

# 完整流程（采集 + 处理 + 发送）
python scripts/main.py

# 仅测试邮件模板
python scripts/main.py --test-email

# 仅采集处理不发送
python scripts/main.py --dry-run
```

## 邮件发送器功能

`EmailSender` 类的主要能力：

1. **HTML 生成**：读取邮件模板，按四大模块生成英文 HTML 邮件
2. **优先级徽章**：P0（重磅/红色）、P1（重要/橙色）自动加标识
3. **Dry-run 模式**：生成 HTML 保存到 `output/preview.html` 预览，不实际发送
4. **模板降级**：若外部模板文件不存在，自动使用内置默认模板

## Delivery Rules For Mixed Source Types

- `official` and `media` items can appear as primary headlines.
- `creator` items are best used as supporting examples, workflow tips, or product demos.
- `community` items should be framed as discussion or signal, not confirmation.
- If the same event exists in official and social form, the official link should be the main CTA.

## Scheduling

For a daily digest, the reliable order is:

1. collect sources from the current allowlist
2. process and deduplicate
3. generate preview
4. send or publish

If the source inventory changes, update 01-collection before touching delivery schedules.

## 故障排除

- **邮件发送失败**：检查 Gmail 是否开启两步验证+应用密码；检查 SMTP 端口是否被防火墙拦截
- **邮件进垃圾箱**：避免标题含过多 emoji；建议配置 SPF/DKIM 记录
- **定时任务不触发**：检查计划任务日志；确保 Python 路径正确

## References

- [../../AI资讯/ai-news-aggregator/scripts/email_sender.py](../../AI资讯/ai-news-aggregator/scripts/email_sender.py)
- [../01-collection/references/nexttoken-source-registry.md](../01-collection/references/nexttoken-source-registry.md)
