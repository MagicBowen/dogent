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

## Release 0.9.7

- Monitor the tool usage of the Agent. If it is found that the agent accesses files outside the working path (whether reading or writing) or deletes files within the working path, it is necessary to confirm with the user first (the original task of the claude agent client should not be interrupted). If the user agrees, continue the task; otherwise, exit the task (shows task abort and reason to user).

---

## Pending Requirements

- Dogent supports configuring Claude's commands, subagents, and skills;
- Dogent supports loading Claude's plugins;
- Dogent supports the ability to generate images;
- Dogent supports mdbook's skill (using the capability of external skill configuration);
- Dogent supports more excellent file templates;
- Provide a good solution for model context overflow;