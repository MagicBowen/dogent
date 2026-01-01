# Original Requirements

## Release 1.0.0

- Optimize the interaction experience when the Agent asks users questions and requests clarification: have an independent question-and-answer interface that displays the total number of questions and the progress; ask questions one by one, and after the user answers, proceed to the next question; 
- for each question, provide users with answer options, allowing them to select by moving the cursor or add free answers. The cursor is by default on the most recommended answer. 
- To achieve this goal, it may be necessary to modify the system prompt so that when the LLM needs the user to answer questions, it organizes the required information such as questions and suggested options in a structured format (e.g., json). Then, the codes extracts this structured content, enters the question-and-answer interactive interface, collects the user's answers, splices all the questions and answers together, and returns them to the LLM for subsequent processing.
- You need to consider whether, in the process of the Agent asking follow-up questions and the user answering questions, in principle, the current loop of the agent client should not exit, otherwise the LLM context will be lost?
- In addition, it is necessary to consider that if the user does not answer for a long time (timeout), the task is regarded as aborted, and the current agent loop is ended.
- In the question-and-answer interaction, the user also has the right to exit and interrupt the task (consider the interaction design, whether to use the same way as the esc interrupt, or need to use other ways to avoid conflicts with the normal exit of the agent loop?).
- For this requirement, you need to have an aesthetically pleasing and user-friendly interaction scheme design;

---

## Pending Requirements

- Dogent supports configuring Claude's commands, subagents, and skills;
- Dogent supports loading Claude's plugins;
- Dogent supports the ability to generate images;
- Dogent supports mdbook's skill (using the capability of external skill configuration);
- Dogent supports more excellent file templates;
- Provide a good solution for model context overflow;