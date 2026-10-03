---
name: resume-screener
description: Hiring managers in #hiring who already have a JD and applicant resumes. Score fit the same way as the Streamlit recruiting assistant. Do not draft a new JD.
---
# Resume screener

This is the Slack version of the Streamlit app. The manager already has a job
description and resumes. Score demonstrated evidence. Do not rewrite the JD.

Tools live at the repo root. Run from that directory.

## When this skill applies

Use this skill when the manager:
- pastes or attaches a finished JD, and
- shares one or more applicant resumes.

Do **not** call draft_role, approve_role, or match_candidates.
Do **not** invent scores. Run the tool and report only what it returns.

## Steps

1. Save the JD exactly as given:
   `cat > /tmp/jd.txt <<'EOF'`
   ...manager JD...
   `EOF`
2. Save uploaded resumes (or pasted text as `NAME.txt`) into `/tmp/applicants/`.
3. Ask once, if they have not already answered:
   "Were the applicants told their public GitHub/LinkedIn may be reviewed?"
4. Run the same pipeline Streamlit uses:

```
python3 -m recruit_assistant.cli screen \
  --title "JOB TITLE FROM THE JD" \
  --jd-file /tmp/jd.txt \
  --resumes /tmp/applicants \
  --format slack
```

Add `--consent-confirmed` only if the manager said yes.
Add `--discover` only if they explicitly ask to search for missing profiles.
Never add `--discover` in the demo.

5. Paste the tool output into Slack. Keep the candidate order the tool used.
   Unknown means the evidence did not show it, never that the person lacks it.
6. End with the tool notice. A person decides. Nothing is rejected automatically.

## Demo files on the laptop

If the manager says to use the local test set:

- JD: `/Users/snehasrikanth/hackathon/Test Resume/Senior_Applied_AI_Scientist_Job_Description.txt`
- Resumes: `/Users/snehasrikanth/hackathon/Test Resume/Edge Cases`

Then run those paths directly instead of `/tmp`.
