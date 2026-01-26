# 工作区状态文件：history / memory / lessons

Dogent 会在 `.dogent/` 下维护若干“状态文件”，用于记录对话进度、临时草稿与经验沉淀。本章解释它们的作用，并介绍相关命令：`/show`、`/archive`、`/clean`。

## 1. 文件与用途

### 1.1 `.dogent/history.json`

- **用途**：记录对话过程与任务进度（结构化 JSON）
- **特点**：用于连续对话、追踪任务上下文
- **提示**：该文件由系统自动维护，不建议手动编辑

### 1.2 `.dogent/memory.md`

- **用途**：临时记忆/草稿缓冲区
- **特点**：仅在需要时生成（非默认就有）
- **提示**：适合存放“中间稿、临时总结”一类内容

### 1.3 `.dogent/lessons.md`

- **用途**：记录 lessons（经验/纠错规则）
- **特点**：每次对话会注入到提示词中，帮助避免重复错误
- **提示**：可手动整理，但建议保持简洁

---

## 2. /show：查看状态

### 查看历史

```text
/show history
```

显示近期对话记录，并包含最新的 todo 视图。

### 查看 lessons

```text
/show lessons
```

展示最近几条 lessons 与文件位置提示。

---

## 3. /archive：归档

```text
/archive [history|lessons|all]
```

- `history`：归档对话历史
- `lessons`：归档 lessons
- `all`：全部归档

归档结果会存入：`.dogent/archives/` 目录。

---

## 4. /clean：清理

```text
/clean [history|lesson|memory|all]
```

- `history`：清理 history
- `lesson`：清理 lessons
- `memory`：清理 memory
- `all`：全部清理（默认）

> 建议在任务结束或项目交接时使用 `clean`。

---

## 5. 使用建议

- **长期项目**：保留 history，便于持续迭代
- **短期任务**：完成后可 archive 或 clean
- **经验沉淀**：保持 lessons 简洁，定期整理

---

下一章进入命令参考手册部分。
