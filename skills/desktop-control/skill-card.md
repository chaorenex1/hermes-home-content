## Description: <br>
Advanced desktop automation with mouse, keyboard, screen capture, window management, clipboard, and autonomous task execution. <br>

This skill is ready for commercial/non-commercial use. <br>

## Publisher: <br>
[matagul](https://clawhub.ai/user/matagul) <br>

### License/Terms of Use: <br>


## Use Case: <br>
Developers and automation builders use this skill to let an agent operate a live desktop through mouse, keyboard, screen observation, clipboard, window management, and application-launch actions. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: The skill can control the live desktop, including keyboard, mouse, windows, screenshots, clipboard, and application launching. <br>
Mitigation: Install it only for intentional desktop-control use, start in an isolated or test session, and keep sensitive applications and secrets out of view. <br>
Risk: Automation actions may run with limited default confirmation. <br>
Mitigation: Keep failsafe enabled and prefer require_approval=True for workflows that type, click, use the clipboard, submit information, post publicly, or operate on files. <br>
Risk: Autonomous workflows can capture or save screenshots and interact with visible applications. <br>
Mitigation: Review each planned action before use in sensitive contexts and avoid autonomous operation when private data is visible. <br>


## Reference(s): <br>
- [ClawHub skill page](https://clawhub.ai/matagul/desktop-control) <br>
- [SKILL.md](artifact/SKILL.md) <br>
- [AI_AGENT_GUIDE.md](artifact/AI_AGENT_GUIDE.md) <br>
- [QUICK_REFERENCE.md](artifact/QUICK_REFERENCE.md) <br>


## Skill Output: <br>
**Output Type(s):** [Code, Shell commands, Configuration, Guidance, Files] <br>
**Output Format:** [Markdown documentation, Python code, shell commands, and runtime desktop actions] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [May create screenshots or image files when screen capture workflows save output to disk.] <br>

## Skill Version(s): <br>
1.0.0 (source: server release metadata) <br>

## Ethical Considerations: <br>
Users should evaluate whether this skill is appropriate for their environment, review any generated or modified files before relying on them, and apply their organization's safety, security, and compliance requirements before deployment. <br>
