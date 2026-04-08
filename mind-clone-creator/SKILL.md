---
name: mind-clone-creator
description: Use when the user wants to create their own digital twin, mind clone, personal AI advisor, or a persona-plus-workflow work clone from their own experience, judgment style, and work habits. Trigger on requests like "创建分身", "工作分身", "数字分身", "克隆自己", "create my clone", "build my work clone", or "把我的经验做成 AI 顾问".
---

# Mind Clone Creator

## Overview

Create the user's own digital twin through structured self-interview.
The foundation is always a persona-layer clone skill for OpenClaw: it restores how the user thinks, judges, responds, and collaborates.
This skill also supports a first-class `persona-plus-workflow` path: keep the workflow track alive from the top-level bundle, then compile blueprint/runtime artifacts after one concrete work unit is defined.
It still does not, by default, claim a full work-replacing agent with autonomous workflow execution, task routing, or stage decisions before that workflow layer is explicitly modeled.

## Use This Skill When

- The user wants to create their own digital twin, mind clone, personal AI advisor, or reusable consultation persona.
- The user wants to package their own experience, judgment style, boundaries, or work habits into an OpenClaw skill.
- The user already has self-authored materials and wants them turned into `clone_config.yaml`, `mind_profile.md`, `system_prompt.md`, and a runnable clone package.
- The user wants to extend that persona into one explicit workflow blueprint for a specific kind of recurring work.
- The user wants both: a clone that sounds like them and a workflow-backed clone for one recurring category of work.

Do not use this skill when:

- The user wants to clone another person. Redirect to `mind-clone-advisor`.
- The user expects a fully autonomous work-replacing agent without workflow-layer design.

## User Flow

Keep the user-visible flow at 5 steps:

1. Build the outline
2. Run the interview
3. Confirm the profile
4. Generate and evaluate automatically
5. Deliver `final` or `draft`

The user only answers questions and confirms the profile.
Environment checks, helper checks, profession research, packaging, and evaluation stay in the background unless they affect a user decision.

## Local Files And Privacy

To support multi-turn progress, this workflow may write local artifacts such as `personal_interview.md`, interview state files, bundle manifests, and generated outputs in the current workspace or chosen output directory.
Treat these as user-controlled local working files, not hidden external storage.
If the user wants a low-retention run, minimize intermediate files when feasible and explain which local files can be deleted after delivery.

## Core Guards

Always enforce these gates:

1. The user is creating their own clone, not cloning another person.
2. The user accepts this is an honest approximation, not perfect replication.
3. The user's own answers, examples, and optional self-provided materials are the source of truth.
4. A `final` clone requires coverage for `identity`, `skills`, `knowledge`, `work_process`, `thinking`, and `expression`.

If the user wants a clone that can replace real work, state clearly that persona is still the foundation.
Start the `persona-plus-workflow` path immediately, keep `workflow_interview.md` active even before the first `target_work_unit` is final, and do not claim workflow artifacts are ready until that target is explicit.

## Helper Skills

`mind-clone-creator` stays the controller skill for the whole workflow.
If helpers are needed, invoke them inside this workflow instead of switching the user onto another primary skill.

Allowed helper patterns:

- bundled `references/multi-search-engine/SKILL.md`: default path for all networked search
- `deep-research`: profession patterns, evaluation scenarios, knowledge-base suggestions
- `content-harvester`: normalize the user's own content into reusable materials
- `docx` / `pdf` / `xlsx`: extract user-provided files
- `tikhub-api-helper`: fetch the user's own platform content
- `find-skills` / `skill-installer`: discover or install missing skills when the real workflow exceeds current capability

Rules:

- Check actual helper availability first; do not assume the user's environment matches the creator environment.
- If a missing helper or external skill is likely needed, surface that right after the outline step, before the deep interview starts.
- Never install or rely on an external skill without user confirmation.
- Helper skills never replace the user's interview answers or the final `draft/final` decision.

## Execution Rules

- Follow [SKILL-OPERATING-STANDARD.md](SKILL-OPERATING-STANDARD.md) for language, privacy, quality, and output rules.
- If `python3` is available, prefer the scripts in `scripts/`; otherwise follow the manual process in `steps/`.
- Ask one interview block at a time. If the user's answer is vague or lacks an example, follow up before moving on.
- If the user asks for the quick version, follow the quick interview path in [steps/02_self_interview.md](steps/02_self_interview.md).
- If the user asks for persona + work clone together, prefer `scripts/bootstrap_working_clone_bundle.py` in `persona-plus-workflow` mode instead of treating workflow as a later side quest.
- Route all web search through `references/multi-search-engine/SKILL.md`.
- Use external research only for profession patterns, realistic evaluation scenarios, and suggested materials. It must never override the user's own stated beliefs or boundaries.
- Use the bundled prompts and templates instead of improvising structured artifacts.
- When using persisted interview state, treat `accept_for_now` as temporary only; validate final readiness before claiming `draft_status: final`.
- Use the rubric in [eval/scoring_rubric.md](eval/scoring_rubric.md) before allowing final output.

## Preferred Entry Points

Use these entrypoints by stage:

- Persona interview start: `scripts/init_personal_interview.py`
- Persona next-question / persisted loop: `scripts/plan_clone_interview_next.py`, `scripts/build_next_interview_update.py`, `scripts/init_clone_interview_state.py`, `scripts/advance_clone_interview_state.py`, `scripts/run_clone_interview_turn.py`
- Bundle bootstrap / refresh / final-readiness: `scripts/bootstrap_working_clone_bundle.py`, `scripts/refresh_working_clone_bundle.py`, `scripts/run_working_clone_until_final.py`, `scripts/validate_working_clone_bundle.py`
- Workflow extension: `scripts/init_workflow_interview.py`, `scripts/validate_workflow_interview.py`, `scripts/build_workflow_blueprint.py`, `scripts/bootstrap_workflow_blueprint.py`, `scripts/build_workflow_clone_skill.py`, `scripts/bootstrap_workflow_clone_runtime.py`
- Final packaging and release gates: `scripts/extract_clone_draft.py`, `scripts/build_clone_config.py`, `scripts/validate_clone_interview_state.py`, `scripts/validate_clone_config.py`, `scripts/render_delivery_summary.py`, `scripts/clone_ops.py validate release-readiness`

Use [references/capability_index.md](references/capability_index.md) for the full script map instead of turning this file into the script catalog.

## Output Contract

Primary deliverables:

- a personal clone skill folder, for example `my-clone-skill/`
- when the user wants persona + workflow together, a working bundle that keeps workflow status explicit until the workflow chain is fully compiled

Inside the personal clone skill:

- `SKILL.md`
- `clone_config.yaml`
- `mind_profile.md`
- `system_prompt.md`
- `eval_report.md`
- `research_digest.md` if profession research was used

Inside the working bundle when workflow is enabled:

- `workflow_interview.md` immediately, even if `target_work_unit` is still pending
- `workflow_blueprint.md`, workflow clone skill, and workflow runtime bundle after `target_work_unit` is defined and the workflow chain is compiled

By default this deliverable can:

- answer in a way closer to the user's reasoning and expression
- preserve boundaries, principles, and preferred work style
- act as a consultation or review proxy in bounded scenarios

By default it does not:

- run multi-stage work end to end
- decide current execution stage for arbitrary jobs
- replace the user's full production work loop without extra workflow design

## Failure And Fallback

- If the user wants to clone someone else, stop and redirect to `mind-clone-advisor`.
- If answers are vague, ask for concrete examples before advancing.
- If the user has no prepared materials, continue by collecting the missing core information through follow-up questions.
- If external research conflicts with the user's own answers, treat the user's answers as primary and mark the research as a tension to review.
- If quality is below 60 or the user's own core answers are still missing, output only a `draft`.
- Even in `draft` mode, still deliver the runnable personal clone files plus a concrete improvement plan.
- If the user explicitly wants a work-replacing clone, switch to the `persona-plus-workflow` path. If the first work category is still unclear, initialize `workflow_interview.md`, keep the blocker visible, and continue packaging the persona layer without pretending the workflow chain is already done.

## Navigation

- Step docs: [steps/00_skill_check.md](steps/00_skill_check.md), [steps/01_profession_parse.md](steps/01_profession_parse.md), [steps/01b_domain_research.md](steps/01b_domain_research.md), [steps/02_self_interview.md](steps/02_self_interview.md), [steps/03_mind_profile.md](steps/03_mind_profile.md), [steps/04_system_prompt.md](steps/04_system_prompt.md), [steps/05_quality_eval.md](steps/05_quality_eval.md), [steps/06_output.md](steps/06_output.md), [steps/07_workflow_agent_design.md](steps/07_workflow_agent_design.md)
- Prompt library: [prompts/profession_analyzer.md](prompts/profession_analyzer.md), [prompts/domain_research_brief.md](prompts/domain_research_brief.md), [prompts/interview_guide.md](prompts/interview_guide.md), [prompts/profile_synthesizer.md](prompts/profile_synthesizer.md), [prompts/prompt_generator.md](prompts/prompt_generator.md), [prompts/workflow_interview_guide.md](prompts/workflow_interview_guide.md), [prompts/eval_question_gen.md](prompts/eval_question_gen.md), [prompts/eval_scorer.md](prompts/eval_scorer.md)
- Script map and operator docs: [references/capability_index.md](references/capability_index.md), [references/operator_playbook.md](references/operator_playbook.md)
- Output formats and examples: [references/personal-clone-skill-format.md](references/personal-clone-skill-format.md), [references/workflow-clone-skill-format.md](references/workflow-clone-skill-format.md), [references/profession-adapter-schema.md](references/profession-adapter-schema.md), [eval/human_review_checklist.md](eval/human_review_checklist.md), `templates/`, `examples/ai_engineer/`
