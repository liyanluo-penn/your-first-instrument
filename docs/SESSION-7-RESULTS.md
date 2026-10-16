# Session 7 作业说明

老师这次要你完成两件事：先让笔记工具知道“谁在使用”，再把数据库和登录功能用到自己的项目里。你的展示项目是作业截止日期倒计时。

## 已完成的内容

| 老师的要求 | 完成情况 |
|---|---|
| 从模板建立 protected-notes 仓库，不要 fork | 已通过 GitHub 模板创建 [your-protected-notes](https://github.com/liyanluo-penn/your-protected-notes)，不是 fork。 |
| 创建或接入 Neon 数据库，并启用登录 | 已复用课程的 my-memory 数据库，启用 Neon Auth。 |
| 部署到 Render | 笔记工具和倒计时项目均已上线，使用免费方案。 |
| 安装到 Claude 或准备 Claude Code 的 `.mcp.json` | 两个连接均已配置，Claude Code 检查显示 Connected。 |
| 应用到自己的 show-and-tell 项目 | 倒计时现在可以保存作业、重新读取、标记完成，并区分私人列表与访客共享列表。代码已合并到 main。 |

没有删除旧仓库。课堂图片里的删除步骤只针对旧 protected-notes 出现问题的情况。

## 你接下来怎么使用

1. 在 Claude Code 中打开这个项目。如果提示登录 Claude，使用你自己的 Claude 账号登录。
2. 输入 `/mcp`，选择相应的连接并完成登录。使用刚才注册的作业账号。刚才的网页登录用于测试，登录凭据没有自动转移给 Claude。
3. 对 Claude 说：“调用 assignment-deadlines 的 `user_status`。”确认返回 `user`，再保存私人内容；`guest` 表示任何访客都能看到的共享列表。
4. 对 Claude 说：“保存一个演示作业，标题是 My presentation，截止时间是 2026 年 10 月 23 日下午 3 点，UTC−04:00。然后列出我的作业和剩余时间。”
5. 开一个新对话，再说：“列出我的作业。”它仍能从数据库读取。最后可以让 Claude 把演示作业标记为完成，再列出包含已完成项目的历史。

这里的日期只是演示例子，不是老师的实际作业截止日期。免费服务闲置后会休眠，第一次连接可能要等约一分钟。

如果使用 Claude 网页版，在连接器设置中添加以下地址，并选择登录、自动注册 OAuth 客户端（DCR）：

| 连接 | 地址 |
|---|---|
| 倒计时项目 | `https://your-first-instrument-a84r.onrender.com/mcp` |
| 保护笔记 | `https://your-protected-notes-0voz.onrender.com/mcp` |

这些是给 Claude 调用的 MCP 地址，不是普通网页首页。

## 展示时可以这样解释

“我原来的工具只能计算距离截止时间还有多久。现在它可以记住我的作业，换一个对话后还能找到。Neon 数据库存储作业，Render 运行工具，Neon Auth 识别用户。访客共享一个演示列表，登录用户有各自的私人列表。错误的登录凭据会被拒绝，避免把私人作业意外保存到公共列表。”

英文展示稿和老师可能追问的问题见 [SHOW-AND-TELL.md](SHOW-AND-TELL.md)。实现和测试有 Codex 协助，代码保留了课程模板的署名。

## 实际验证结果（2026-10-15）

- 20 项自动化测试通过：日期计算、数据库保存、用户隔离、非法凭据、OAuth 流程等。
- 两个线上服务均验证了访客保存与跨会话读取、非法 token 拒绝。
- 你亲自完成真实 Neon Auth 登录后，验证了两个服务的私人保存与跨会话读取；访客看不到私人记录，也不能完成你的私人截止日期。
- 登录会话续期通过；Claude Code 的两个 MCP 连接均显示 Connected。
- 两个不同登录身份之间的隔离通过本地测试；线上测试使用你的一个账号和访客。
- 测试数据已清理，没有清空任何原有列表。连接密码和 token 没有写进 GitHub。

课堂演示时仍需在 Claude 内完成自己的账号登录。作业尚未提交到课程网站；当前成果是已上线的 GitHub 项目和展示材料。
