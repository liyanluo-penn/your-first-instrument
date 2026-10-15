# Show and tell: my private assignment deadline assistant

## What to explain

“My first tool calculated how much time remained until a deadline. I extended it so Claude can save my assignments and retrieve them in a later conversation. Postgres keeps the data, Render runs the server, and Neon Auth identifies the user. Guests share a demonstration list. Signed-in users have separate private lists. An invalid login causes an error instead of silently saving to the public list.”

中文理解：原来的工具只会计算倒计时；现在它还能记住作业，并分清是谁的作业。数据库负责保存，Render 负责运行，登录系统负责确认身份。

## Live demo

Use invented demonstration assignments, not personal information in guest mode. The dates below are examples, not actual course deadlines.

1. Connect as a guest and ask: “Call `user_status`. Then save a demo assignment called Public practice, due October 22, 2026 at 11:59 PM, UTC−04:00.”
2. Ask: “List my deadlines and tell me how long remains.” A second guest connected to the same service should see Public practice.
3. Sign in and ask `user_status` again. Confirm the mode is `user` before continuing.
4. Ask: “Save My presentation, due October 23, 2026 at 3 PM, UTC−04:00. Then list my deadlines.” The private list should contain this assignment and exclude Public practice.
5. Switch to guest or a different signed-in account. Ask for deadlines. My presentation should be absent.
6. Return to the original signed-in account and mark My presentation complete using its returned id. Ask to include completed assignments to show the preserved history.

## Questions the instructor may ask

- **What survives a new chat?** The saved assignments in Neon. The model needs to call the tool again to retrieve them.
- **What makes them private?** The server verifies a signed identity token, takes its stable user id, and filters every database read/update by that id.
- **What happens if login expires?** The server rejects invalid credentials. It does not downgrade the request to guest.
- **Why require a timezone?** “Friday at midnight” is ambiguous; an explicit offset makes the countdown verifiable.
- **What did I adapt?** The course's clock starter and protected-notes authentication pattern, with Codex assistance. The added deadline storage, ownership checks, tests, and design decisions are in this repository.

Only describe live deployment and sign-in as completed after actually running those checks. Use the test output to describe automated checks separately.
