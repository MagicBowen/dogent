- move dogent_schema.json from dogent/templates to dogent/schemas
- rename the dogent/templates to 
- move the doc_templates folder under dogent folder directly, and rename to templates

- move prompt in lesson_draft.py to single md
```py
    async def _run_llm(self, user_prompt: str) -> str:
        system_prompt = (
            "You write concise, reusable engineering lessons in Markdown.\n"
            "Return ONLY Markdown (no code fences). Start with a '## ' heading.\n"
            "Then include sections: ### Problem, ### Cause, ### Correct Approach.\n"
            "The title must be a specific actionable rule derived from the user correction.\n"
            "Be brief: prefer bullets; avoid long prose.\n"
            "The Correct Approach MUST include the user's correction verbatim as a short quote block.\n"
        )
```

- CLI 中的 markdown editor 的功能独立一个文件