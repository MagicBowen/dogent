# Dogent Writing Configuration

> This file defines the core requirements for document writing in the current working directory.
> 
> **Configuration Guide**:
> - `[Configured]` indicates a value explicitly set by the user
> - `[Default]` indicates the current default value (not modified by user)
> - `Options:` lists all available choices for reference
> - To modify a setting, remove `[Default]` and enter your choice

---

## Basic Information

**Project Name**: [Default] Unnamed Project
<!-- Example: [Configured] My Technical Blog -->

**Primary Language**: [Default] English
<!-- Options: English | 中文 | 日本語 | Other -->

---

## Target Audience

**Audience Type**: [Default] General Readers
<!-- Options: General Readers | Professionals | Technical Staff | Students | Business Managers | Researchers -->
<!-- Or custom: [Configured] Backend developers with 3+ years of experience -->

**Expertise Level**: [Default] Intermediate
<!-- Options: Beginner | Intermediate | Advanced | Expert -->

**Expected Background Knowledge**: [Default] No special requirements
<!-- Example: [Configured] Readers should understand basic programming concepts and Python syntax -->

---

## Writing Style

**Overall Style**: [Default] Semi-formal
<!-- Options: Formal | Semi-formal | Casual | Academic | Technical Documentation | Creative Writing | Journalistic -->

**Tone**: [Default] Objective and Neutral
<!-- Options: Objective and Neutral | Warm and Friendly | Authoritative and Professional | Plain and Accessible | Humorous | Serious and Solemn -->

**Point of View**: [Default] Third Person
<!-- Options: First Person | First Person Plural (We) | Second Person | Third Person -->

**Special Style Requirements**: [Default] None
<!-- 
Example:
[Configured]
- Avoid jargon; when necessary, include explanations
- Illustrate each important concept with practical examples
- Use active voice; avoid passive constructions
- Use transition sentences between paragraphs
-->

---

## Document Format

**Output Format**: [Default] Markdown
<!-- Options: Markdown | HTML | Plain Text | reStructuredText | AsciiDoc -->

**Heading Levels**: [Default] Up to 3 levels
<!-- Options: Up to 2 levels | Up to 3 levels | Up to 4 levels | Up to 5 levels -->

**Paragraph Length**: [Default] No restriction
<!-- Options: Brief (1-2 sentences) | Standard (3-5 sentences) | Detailed (5-8 sentences) | No restriction -->

**List Usage**: [Default] As needed
<!-- Options: Avoid when possible | Use moderately | As needed | Prefer lists -->

**Code Block Style**: [Default] With language annotation
<!-- Options: With language annotation | Without annotation | No code blocks -->

---

## Length Requirements

**Default Length**: [Default] No restriction
<!-- 
Options:
- Brief: 300-500 words
- Short: 500-1000 words
- Medium: 1000-3000 words
- Long: 3000-10000 words
- Extended: 10000+ words (will be processed in segments)
- No restriction: Adjust automatically based on content needs
-->

**Length Flexibility**: [Default] Allow ±20% variance
<!-- Options: Strict adherence | Allow ±10% variance | Allow ±20% variance | Allow ±50% variance | Fully flexible -->

---

## Content Structure

**Required Sections**: [Default] Plan as needed
<!--
Preset Options:
- Plan as needed: Determine structure based on article type and user requirements
- Basic structure: Introduction + Body + Conclusion
- Complete structure: Abstract + Introduction + Body + Conclusion + References
- Tutorial structure: Overview + Prerequisites + Step-by-step Guide + FAQ + Summary
- Technical documentation: Overview + Installation/Configuration + Usage + API Reference + Troubleshooting
- Research report: Abstract + Background + Methods + Results + Discussion + Conclusion
- Custom: See configuration below

Custom Example:
[Configured] Custom Structure
- Opening introduction (Required)
- Problem analysis (Required)
- Solution (Required)
- Implementation steps (Optional)
- Impact assessment (Required)
- Extended thoughts (Optional)
-->

---

## Citations and Sources

**Citation Style**: [Default] Simple notation
<!-- Options: APA | MLA | Chicago | IEEE | Simple notation | Footnotes | No citations needed -->

**Fact-checking Level**: [Default] Standard
<!--
Options:
- Strict: All factual statements must be supported by reliable sources with cross-verification
- Standard: Key facts need verification; common knowledge does not require verification
- Relaxed: Verify only questionable content
- None: For creative writing or scenarios that do not require fact-checking
-->

**Source Priority**: [Default] Balanced use
<!--
Options:
- Local only: Use only local knowledge base; no web search
- Prefer local: Prioritize local knowledge base; supplement with web when necessary
- Balanced use: Treat local and web sources equally
- Prefer web: Prioritize the latest web information
- Web only: Do not use local files as references
-->

---

## Quality Standards

**Originality Requirement**: [Default] Comprehensive paraphrasing
<!--
Options:
- Highly original: Reference sources for facts only; expression must be entirely original
- Comprehensive paraphrasing: Synthesize multiple sources and rephrase in your own words
- Moderate citation: Allow limited direct quotes; main content must be original
- Compilation: Primarily organize existing materials with source attribution
-->

**Readability Target**: [Default] Generally readable
<!--
Options:
- Simple and easy: Understandable by upper elementary school students
- Generally readable: Understandable by average adult readers
- Professionally readable: Understandable by those with basic domain knowledge
- Academic level: For professional researchers
-->

---

## Prohibited Items

**Content Restrictions**: [Default] Standard prohibitions
<!--
Default Prohibitions (Always Active):
- Do not fabricate false information or data
- Do not use discriminatory or offensive language
- Do not make absolute claims without evidence

Optional Additional Prohibitions (Enable as Needed):
[ ] Do not use first person
[ ] Do not use rhetorical questions
[ ] Do not use internet slang
[ ] Do not use English terms (must translate)
[ ] Do not make subjective evaluations
[ ] Do not use metaphors or analogies
[ ] Other: ___

Configuration Example:
[Configured] 
- Standard prohibitions (retained)
- Enabled: Do not use internet slang
- Enabled: Do not use first person
- Custom: Do not mention competitor company names
-->

---

## Local Knowledge Base

**Reference Directories**: [Default] Current directory and subdirectories
<!--
Configuration Example:
[Configured]
- ./references/    # Primary reference materials
- ./docs/          # Existing documentation
- ./data/          # Data files
- Exclude: ./drafts/  # Do not reference drafts directory
-->

**File Types**: [Default] Common text formats
<!--
Default Supported: .md, .txt, .json, .yaml, .xml, .html, .csv
Extendable: .pdf (requires tool support), .docx (requires tool support)

Configuration Example:
[Configured] Process only .md and .txt files
-->

---

## Output Configuration

**Output Directory**: [Default] Current directory
<!-- Configuration Example: [Configured] ./output/ -->

**File Naming**: [Default] Auto-generate based on title
<!--
Options:
- Auto-generate based on title
- Date prefix: YYYY-MM-DD-title
- Number prefix: 001-title
- Custom template: ___

Configuration Example: [Configured] Date prefix: YYYY-MM-DD-title
-->

---

## Special Instructions

**Project-specific Requirements**: [Default] None
<!--
Add any special requirements not covered by the options above.

Configuration Example:
[Configured]
1. Each article must begin with a "30-Second Overview" summary box
2. Technical terms must include the original English in parentheses on first occurrence
3. All external links must be collected in an "Further Reading" section at the end
4. Code examples must include complete runnable code; do not use ellipses
-->

---

## Configuration Status

> **This File's Configuration Status**: [Not Configured] 
> 
> Change the above to `[Configured]` to indicate you have reviewed and confirmed the configuration.
> If left as `[Not Configured]`, Dogent will use all default values.

---

## Version History

| Date | Changes | Status |
|------|---------|--------|
| {{CREATION_DATE}} | Initial creation | Not Configured |
<!-- | 2025-01-15 | Configured target audience and writing style | Partially Configured | -->
<!-- | 2025-01-20 | Completed all configuration | Configured | -->