# Original Requirements

---

## Release 0.9.19

- Add the image generation capability, refer to this document：`dev/spikes/image_generate.md`, implement and register an image generation capability tool for the agent, and note that the requirements for image generation should be made into various parameters of the tool.
- Add a new profile config for image generation (as same as the vision_profile), user should config the api-key;
- User could config the profile of image generation through `/profile` command;

## Release 0.9.20

When I use dogent in a new environment, when dogent uses the `mcp__dogent__export_document` tool, the CLI enters a very long waiting state. I guess it might be because the new environment lacks some related dependency libraries and software, and dogent is downloading them? Please help me check the external dependencies here. I hope to optimize the implementation related to this: when dogent executes the `mcp__dogent__export_document` tool (or other mcp tools that have the ENV depencencies), it first checks the relevant dependencies. If they are not installed in the corresponding OS, it needs to ask the user whether to assist in downloading and installing by dogent now or let the user install manually. If the user chooses to install automatically now, a friendly progress bar needs to be displayed for each download and installation process. If the user chooses to install by themselves, prompt the user with the installation method and interrupt the current task.

---

## Pending Requirements

[support more document template]
- resume
- research report
- blog
- software design document
- software usage manual

[support more generation mode]
- Dogent supports the ability to generate PPT;

[support downloading dependencies when runing]
- mcp__dogent__export_document

[support mutiple language]
- support multiple languages: en & zh;
