# 文档导出与格式转换

Dogent 提供面向文档的导出与转换能力，适合将 Markdown 转成 PDF/DOCX，或将 DOCX/PDF/XLSX 转回 Markdown 进行再编辑。

## 1. 能力概览

- **读取文档**：PDF / DOCX / XLSX / 纯文本
- **导出 Markdown**：导出为 PDF 或 DOCX
- **格式转换**：DOCX ↔ Markdown、Markdown → PDF、DOCX → PDF
- **PPT**：目前没有找到完美的解决方案，暂时默认使用 “Claude PPTX skill”，详情请参阅：https://github.com/anthropics/skills/tree/main/skills/pptx

所有路径均使用 **工作区相对路径**。

---

## 2. 常见使用方式（写法示例）

### 导出 Markdown

```text
请将 docs/report.md 导出为 PDF，保存到 exports/report.pdf。
```

或：

```text
将 docs/report.md 导出为 DOCX，保存为 exports/report.docx。
```

### 格式转换

```text
把 docs/spec.docx 转为 Markdown，输出到 docs/spec.md。
```

如果你希望提取 DOCX 中的图片：

```text
把 docs/spec.docx 转成 Markdown，图片保存到 assets/images。
```

### 阅读文件内容

```text
请读取 @docs/brief.pdf 并总结要点。
```

对于 Excel：

```text
@data/sales.xlsx#Q4 请根据该表生成分析小结。
```

---

## 3. 导出与转换的细节说明

### 3.1 DOCX 导出

- 导出 DOCX 时会尝试包含本地图片
- 支持 Markdown 图片语法和简单 HTML 图片标签

示例：

```markdown
![](../images/1.png)
```

或者

```markdown
<div align="center"><img src="../images/2.png" width="70%"></div>
```

### 3.2 PDF 样式（CSS）

PDF 导出支持自定义样式：

- 全局样式：`~/.dogent/pdf_style.css`
- 工作区样式：`.dogent/pdf_style.css`（优先级更高）

你可以用下面的写法强制分页：

```html
<div class="page-break"></div>
```

### 3.3 DOCX ↔ Markdown 转换

- DOCX → Markdown 可选择导出图片目录（`extract_media_dir`）
- DOCX → PDF 的实现为：**DOCX → Markdown → PDF**，版式可能略有差异

### 3.4 PDF 依赖与下载提示

- PDF 导出与转换依赖 **Pandoc** 和 **Chrome**。
- 如果本地缺失依赖，Dogent 会提示是否先下载再继续。

---

## 4. 常见问题

- **导出失败或格式异常**：通常是 Pandoc 缺失或不可用，请先确保系统可用。
- **路径错误**：所有路径都必须在工作区内，且输出路径需要包含目标扩展名。

---

下一章将介绍 Lesson（经验沉淀与自动提醒机制）。
