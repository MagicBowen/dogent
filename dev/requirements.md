# Original Requirements

---

## Release 0.9.5

- I hope that dogent can handle pdf / docx / xlsx files. This includes correctly reading the content in these types of files if the user references them using `@` (for now, pdf files can only support text-based PDFs; for other unsupported pdf file types, after detection and identification, it is necessary to return a failure to the user and clearly inform them of the reason).
- I hope that if the user specifies the output type of the document as a pdf or docx file, then dogent can correctly generate pdf and docx files.
- The document(PDF/DOCX) reading and generation can be referred to `dev/spikes/doc_convert.md` and examples in `claude-agent/sdk/skills/skills/pdf/*`、`claude-agent/sdk/skills/skills/docx/*` and `claude-agent/sdk/skills/skills/xlsx/*`, You need to synthesize the characteristics of dogent based on these examples and provide me with the best design solution choice.
- when I told agent to "convert a docx file to markdown file and extract all images in specified path", the agent used the `pandoc` app execute the task (`pandoc "src.docx" -t markdown -o "dst.md" --extract-media=./images`)，This depends on the user's machine app install state. I hope to build the file format conversion capability into dogent. Therefore, please check if this can be done using Python itself, such as with the help of pypandoc. Can we create an mcp specifically for converting between docx, pdf, and markdown?

## Release 0.9.6

- I hope that dogent cann handle off images or video files. if the user references images or vidios using `@`, dogent can post the image/video  to a configured vision llm to get the content details and add the content in the user prompt so that the writting LLM can understand the detailed content in the images/videos. 
- You can refer `dogent/dev/spikes/GLM-4V-Vision-Model-Research-Report.md`，user can select different vision model by dogent.json(maybe the vision profiles in ~/.dogent)

---

## Pending Requirements

- 监控 Agent 的工具使用，发现 agent 访问工作路径之外的文件（无论读写），或者删除工作路径之内的文件，需要先与用户确认，用户同意了才能访问
- `DocumentTemplateManager` 类中读取文档模板生成模板概要的函数实现： `def _extract_intro(self, content: str) -> str` 中目前的逻辑是获取 `## Introduction` 的段落内容，但是可能有的模板没有 `## Introduction` 段落，这时可以变为读取其文档前 5 行，以增加鲁棒性；
- 测试 dogent 加载正常的 claude 的 commands 和 skill 等配置？
- 解决上下文溢出问题
- 增加处理 excel 还有 csv 的能力
- 增加使用 mdbook 等 skill ？
- 读图 和 生成图的能力

