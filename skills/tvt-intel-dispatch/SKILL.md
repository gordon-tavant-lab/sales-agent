---
name: tvt-intel-dispatch
description: Dispatch parallel ECS Fargate agents to research multiple prospects simultaneously — use when 3+ independent intel pipelines need to run at once
source: auto-extracted 2026-06-06
eval:
  mode: gate
  depth: standard
---

# Intel Dispatch — Parallel Agent Fleet

## When to use
- 3+ independent research targets need the same pipeline (deep intel, factcheck, fanout)
- Each target has a `.claude-loop-criteria.md` file defining the research pipeline
- Time-sensitive: running sequentially would take hours

## Prerequisites
- AWS auth working: `AWS_PROFILE=<your-aws-profile> aws sts get-caller-identity`
- ECS cluster `claude-agents` is ACTIVE
- Task definition `claude-agent:4` is registered
- Each prospect folder has `intel/.claude-loop-criteria.md`

## Approach

### 1. Verify infrastructure
```bash
AWS_PROFILE=<your-aws-profile> aws ecs describe-clusters --clusters claude-agents --region us-east-1
```

### 2. Prepare prompts from loop criteria
For each prospect, read their `.claude-loop-criteria.md` and construct the AGENT_PROMPT:
- Include the prospect name, research pipeline stages, exit criteria
- Keep under 4000 chars (ECS env var limit)

### 3. Launch agents (one `run-task` per prospect)
```bash
AWS_PROFILE=<your-aws-profile> aws ecs run-task \
  --cluster claude-agents \
  --task-definition claude-agent:4 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-035e26d51ad978ba1],securityGroups=[sg-07133baca6d2fa68a],assignPublicIp=ENABLED}" \
  --overrides "{\"containerOverrides\":[{\"name\":\"claude-agent\",\"environment\":[{\"name\":\"AGENT_PROMPT\",\"value\":\"PROMPT\"},{\"name\":\"AGENT_NAME\",\"value\":\"NAME\"}]}]}" \
  --region us-east-1
```

### 4. Monitor fleet
```bash
AWS_PROFILE=<your-aws-profile> aws ecs list-tasks --cluster claude-agents --region us-east-1
AWS_PROFILE=<your-aws-profile> aws ecs describe-tasks --cluster claude-agents --tasks ARN1 ARN2 ...
```

### 5. Collect results
Results persist to S3 workspace. Check each prospect's `intel/` folder after tasks complete.

## Pitfalls
- **Env var size limit**: Keep AGENT_PROMPT under 4KB; reference S3 files for long prompts
- **Fargate cold start**: ~60s to pull image; tasks show PENDING before RUNNING
- **Security group**: Must use `sg-07133baca6d2fa68a` (agent-fleet-sg), NOT default SG
- **Public IP required**: Agents need internet for web research; `assignPublicIp=ENABLED`
- **Cost**: Each agent = ~$0.05/hr (1 vCPU, 2GB); terminate after use

## Quality gate
After agents complete, run factcheck on each output before marking ready for outreach.

## Output Gate (mandatory before finishing)

Before finishing, gate the artifact: `/tvt-core-eval gate --output <artifact> --criteria ${CLAUDE_PLUGIN_ROOT}/rubrics/intel-research.md`. Do not hand it off until it passes.

This orchestrator's per-prospect leaf runs already carry their own factcheck step; nothing extra to add here.
