# Original Requirements


---

## Release 0.9.30

- change the folder claude/skills to a git submodule of https://github.com/anthropics/skills for auto sync from the source.
- remove the pptx and skill-creator in the path dogent/plugins/claude/skills, and setup a manifiest file for me to decide which skills I want to copy from claude/skills (git submodule) when package and publish dogent.
- before copying skills from claude/skills to dogent, update the claude/skills git submodule to the newest upstream version first. If the update fails, continue using the currently checked-out submodule version.

---

## Pending Requirements

[support more document template]
- resume
- tech report
- blog
- software design document
- software usage manual
- consultant proposal

[support mutiple languages]
- support multiple languages: en & zh;

[support textual & web]

- https://github.com/Textualize/textual
