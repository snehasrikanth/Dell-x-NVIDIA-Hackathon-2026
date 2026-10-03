import argparse
import json
from pathlib import Path

from fastapi import HTTPException

from recruit_assistant.models import ResearchRequest, ResearchRun
from recruit_assistant.research import run_research
from recruit_assistant.storage import create_job_intake_from_paths, get_job

FIT_LABELS = {
    "strong_role_alignment": "Strong demonstrated alignment",
    "potential_role_alignment": "Potential alignment — review needed",
    "insufficient_demonstrated_evidence": (
        "Insufficient demonstrated evidence — review needed"
    ),
    "analysis_unavailable": "Analysis unavailable — review needed",
}


def format_slack_report(run: ResearchRun, job_name: str) -> str:
    """Short Slack-safe report of the same scores Streamlit shows."""
    lines = [
        f"*Fit review: {job_name}*",
        "Same evidence-first scoring as the Streamlit app. This is not a hiring decision.",
    ]
    shortlisted = [
        candidate
        for candidate in run.candidates
        if candidate.fit_analysis.decision
        and candidate.fit_analysis.decision.top_30_percent
    ]
    if shortlisted:
        lines.append("*Top 30% for human review*")
        for candidate in sorted(
            shortlisted,
            key=lambda item: item.fit_analysis.decision.shortlist_rank or 999,
        ):
            decision = candidate.fit_analysis.decision
            score = (
                f"{decision.evidence_score:.1f}/100"
                if decision.evidence_score is not None
                else "n/a"
            )
            lines.append(
                f"• #{decision.shortlist_rank} {candidate.original_filename} — {score}"
            )

    ordered = sorted(
        run.candidates,
        key=lambda item: (
            item.fit_analysis.decision.evidence_score
            if item.fit_analysis.decision
            and item.fit_analysis.decision.evidence_score is not None
            else -1
        ),
        reverse=True,
    )
    for candidate in ordered:
        analysis = candidate.fit_analysis
        decision = analysis.decision
        lines.append(f"*{candidate.original_filename}*")
        if decision is None:
            lines.append(f"• {analysis.summary}")
            continue
        score = (
            f"{decision.evidence_score:.1f}/100"
            if decision.evidence_score is not None
            else "unavailable"
        )
        lines.append(
            f"• Score {score} · {FIT_LABELS.get(decision.fit_label, decision.fit_label)}"
        )
        lines.append(
            f"• Required criteria {decision.required_criteria_met}/"
            f"{decision.required_criteria_total} · coverage "
            f"{decision.evidence_coverage:.0f}%"
        )
        if decision.hard_requirement_gaps:
            lines.append(
                "• Hard gaps: " + "; ".join(decision.hard_requirement_gaps[:3])
            )
        if analysis.strengths:
            lines.append("• Strengths: " + "; ".join(analysis.strengths[:2]))
        if analysis.unknowns:
            lines.append(
                "• Evidence did not show: " + "; ".join(analysis.unknowns[:2])
            )
    lines.append(run.safety_notice)
    return "\n".join(lines)


def _print_error(exc: Exception) -> int:
    detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
    print(json.dumps({"error": detail}, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agent-callable tools for the evidence-first recruiting assistant."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    research = subparsers.add_parser(
        "research-job",
        help="Research candidate-provided profiles and analyze job fit with local Qwen.",
    )
    research.add_argument("--job-id", required=True)
    research.add_argument(
        "--consent-confirmed",
        action="store_true",
        help="Confirm candidates received notice/consented to professional-source research.",
    )

    screen = subparsers.add_parser(
        "screen",
        help="One-shot Streamlit-equivalent: JD file + resumes -> fit scores.",
    )
    screen.add_argument("--jd-file", required=True, type=Path)
    screen.add_argument("--resumes", nargs="+", required=True, type=Path)
    screen.add_argument("--title", default="Uploaded role")
    screen.add_argument(
        "--consent-confirmed",
        action="store_true",
        help="Read GitHub/LinkedIn links written on the resume.",
    )
    screen.add_argument(
        "--discover",
        action="store_true",
        help="Also search for unlinked public profiles. Off unless asked.",
    )
    screen.add_argument(
        "--format",
        choices=("json", "slack"),
        default="slack",
    )

    args = parser.parse_args()
    try:
        if args.command == "research-job":
            job = get_job(args.job_id)
            run = run_research(
                job,
                ResearchRequest(consent_confirmed=args.consent_confirmed),
            )
            print(run.model_dump_json(indent=2))
            return
        if args.command == "screen":
            if not args.jd_file.is_file():
                raise FileNotFoundError(f"JD file not found: {args.jd_file}")
            if args.discover and not args.consent_confirmed:
                raise ValueError("--discover needs --consent-confirmed")
            job = create_job_intake_from_paths(
                args.title,
                args.jd_file.read_text(encoding="utf-8"),
                args.resumes,
                professional_research_consent=args.consent_confirmed,
            )
            run = run_research(
                job,
                ResearchRequest(
                    consent_confirmed=args.consent_confirmed,
                    use_candidate_provided_links=args.consent_confirmed,
                    discover_public_profiles=args.discover,
                ),
            )
            if args.format == "json":
                print(
                    json.dumps(
                        {
                            "intake_id": job.job_id,
                            "run_id": run.run_id,
                            "job_name": job.job_name,
                            "shortlist_count": run.shortlist_count,
                            "slack": format_slack_report(run, job.job_name),
                            "run": json.loads(run.model_dump_json()),
                            "notice": run.safety_notice,
                        },
                        indent=2,
                    )
                )
            else:
                print(format_slack_report(run, job.job_name))
    except (HTTPException, FileNotFoundError, ValueError, OSError) as exc:
        raise SystemExit(_print_error(exc)) from exc


if __name__ == "__main__":
    main()
