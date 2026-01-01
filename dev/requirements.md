# Original Requirements

---

## Release 0.9.8

- I hope to configure by layers. Users can set global configurations under `~/.dogent` folder. Then, the default values of the `.dogent.json` created in each working directory will be the same as the global configurations. Users can modify the configurations in the working directory separately, which will only apply to the current working directory. 
- If the user does not configure `.dogent.json` in the working directory, it will default to the global settings under `~/.dogent`. 
- If there is no global configuration either, then llm_profile will read the environment variables as it does now, and all other configurations will follow the default values. 
- The default value of web_profile is `default` as it does now, and the default value of vision_profile should be `null` (so that when the user uses `@image` to reference image, an error will be reported to the user, following the fail-fast principle).
- When the setting of vision_profile is `null` (or missing), disable the related mcp tools for agent.
- Users can specify the temporary use of a specific doc template in the input prompt, similar to referencing a file using `@`. We need to design an appropriate symbol (to minimize conflicts with other normal inputs) such that when the user enters it in the prompt, a dropdown list of doc templates will pop up for the user to select (with behavior similar to selecting a file).

---

## Release 0.9.9

- Currently, the markdown to pdf conversion function generates pdfs with a default style. I hope to conduct research based on the current solution to find out the ways to specify styles for the generated pdfs. I hope there can be a style file, which is placed in the `~/.dogent` directory when dogent is started for the first time, serving as the global pdf style, and this style will be used by default when generating pdfs. Users can add and modify their own local style files under `.dogent` in the workspace, and such local style files should be used with priority.
- If a user temporarily specifies a template for writing using `@@`, this template should not be injected into the system prompt (the system prompt doc template can be cleared). The template specified by the user must be injected into the user prompt as a separate remark segment. Update the system prompt to state that when a user prompt remarks a specific template, it takes priority over `.dogent.json` and any inconsistencies in `.dogent.md`.

---

## Pending Requirements

- Dogent supports configuring Claude's commands, subagents, and skills;
- Dogent supports loading Claude's plugins;
- Dogent supports the ability to generate images;
- Dogent supports mdbook's skill (using the capability of external skill configuration);
- Dogent supports more excellent file templates;
- Provide a good solution for model context overflow;
