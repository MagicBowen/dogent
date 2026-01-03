# Issues

- BugFix：工具使用监控，不要删除和读取的权限控制没有生效！考虑在中间出现的时候，需要询问用户，不要打断当前流程！
- 如果agent执行任务的过程中要更新已存在的 .dogent/dogent.md 文件，每次都需要先请求用户授权，经过用户的同意才可以更新,否则不要更新
- 优化欢迎 dogent 的 panel，完善 help panel； 完善各个引导语（包括提示 ctrl + E 启动 editor）