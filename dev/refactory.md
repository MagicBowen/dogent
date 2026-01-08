Here are suggestions for refactoring the code of dogent：
- Decouple and reasonably split all oversized files, such as `dogent/cli.py` is too large and needs to be split and decoupled (Perhaps decouple the two types of editor and preview mode from cli...)
- All complex multi-line prompts and templates in the code should be separated into well-named files instead of being hard-coded in the code， such as below：
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
- There are quite a lot of files under "dogent" now. According to functional modules and reusability, different code files should be placed in appropriate subdirectories.
- move all json schema files into `dogent/schema`, such as dogent_schema.json
- rename the `dogent/templates` to `dogent/configs`
- move the `dogent/configs/doc_templates` to `dogent/templates` that is under dogent folder directly and rename from doc_templates to templates.
- Simplify the content in the startup dogent panel, retaining only the necessary introductions and important reminders. Supplement the help panel with as comprehensive a functional introduction as possible.
- Write the new software architecture and main design into `docs/dogent_design.md`, and use mermaid to complete the main design diagrams such as logical architecture and physical architecture;
- Refactor `docs/usage.md` to introduce all functions of dogent in a complete end-to-end manner, step by step, with examples;