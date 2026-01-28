#!/usr/bin/env python3
"""Extract action items and key decisions from a meeting transcript."""

import argparse
import json
import re
from datetime import datetime
from typing import List, Dict, Optional

DATE_PATTERNS = [
    r"\b(\d{4}-\d{2}-\d{2})\b",  # 2025-01-31
    r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b",  # 1/31/2025
    r"\b(\w+\s+\d{1,2},\s+\d{4})\b",  # January 31, 2025
]

SPEAKER_RE = re.compile(r"^\s*([A-Z][\w .'-]{1,50})\s*:\s*(.+)$")

ACTION_PATTERNS = [
    r"\bI(?:'|’)?ll\s+([^\.\n]+)",
    r"\bI(?:'|’)?m\s+going\s+to\s+([^\.\n]+)",
    r"\bI\s+will\s+([^\.\n]+)",
    r"\bYou\s+should\s+([^\.\n]+)",
    r"\bWe\s+should\s+([^\.\n]+)",
    r"\bLet(?:'|’)?s\s+([^\.\n]+)",
    r"\bAction\s*:\s*([^\.\n]+)",
]

DECISION_PATTERNS = [
    r"\bWe\s+decided\s+(?:to\s+)?([^\.\n]+)",
    r"\bDecision\s*:\s*([^\.\n]+)",
    r"\bAgreed\s+to\s+([^\.\n]+)",
    r"\bWe\s+agree\s+to\s+([^\.\n]+)",
]

DUE_DATE_RE = re.compile(
    r"\b(by|before|due|on)\s+([A-Za-z]+\s+\d{1,2}(?:,\s*\d{4})?|\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})\b",
    re.IGNORECASE,
)

PARTICIPANTS_RE = re.compile(r"\bParticipants?\s*:\s*(.+)", re.IGNORECASE)


def _normalize_date(raw: str) -> str:
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw


def extract_meeting_date(text: str) -> Optional[str]:
    for pattern in DATE_PATTERNS:
        m = re.search(pattern, text)
        if m:
            return _normalize_date(m.group(1))
    return None


def extract_participants(lines: List[str]) -> List[str]:
    participants = set()
    for line in lines:
        speaker = SPEAKER_RE.match(line)
        if speaker:
            participants.add(speaker.group(1).strip())
        else:
            pm = PARTICIPANTS_RE.search(line)
            if pm:
                names = re.split(r",|;|\band\b", pm.group(1))
                for name in names:
                    name = name.strip()
                    if name:
                        participants.add(name)
    return sorted(participants)


def _find_due_date(text: str) -> Optional[str]:
    m = DUE_DATE_RE.search(text)
    if not m:
        return None
    return _normalize_date(m.group(2))


def _clean_task(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().rstrip(";,. ")


def extract_action_items(lines: List[str]) -> List[Dict[str, Optional[str]]]:
    items = []
    current_speaker = None
    for line in lines:
        speaker = SPEAKER_RE.match(line)
        content = line
        if speaker:
            current_speaker = speaker.group(1).strip()
            content = speaker.group(2).strip()

        for pat in ACTION_PATTERNS:
            m = re.search(pat, content, re.IGNORECASE)
            if not m:
                continue
            task_text = _clean_task(m.group(1))
            if not task_text:
                continue
            assignee = None
            if re.search(r"\bI\b|I(?:'|’)?ll|I\s+will|I(?:'|’)?m\s+going", content, re.IGNORECASE):
                assignee = current_speaker
            elif re.search(r"\bYou\s+should\b", content, re.IGNORECASE):
                # Attempt to infer addressee from previous speaker label
                assignee = None
            action = {
                "assignee": assignee,
                "task": task_text,
                "due_date": _find_due_date(content),
            }
            items.append(action)
            break
    return items


def extract_decisions(lines: List[str]) -> List[str]:
    decisions = []
    for line in lines:
        content = line
        speaker = SPEAKER_RE.match(line)
        if speaker:
            content = speaker.group(2).strip()
        for pat in DECISION_PATTERNS:
            m = re.search(pat, content, re.IGNORECASE)
            if m:
                decision = _clean_task(m.group(1))
                if decision:
                    decisions.append(decision)
                break
    return decisions


def build_summary(action_items: List[Dict[str, Optional[str]]], decisions: List[str]) -> str:
    if not action_items and not decisions:
        return "No explicit action items or decisions were detected in the transcript. The meeting appears to be informational or exploratory. Review the transcript for any implied follow-ups."

    parts = []
    if decisions:
        parts.append(f"Key decisions were made on {len(decisions)} topic(s), including: {decisions[0]}")
    if action_items:
        first = action_items[0]
        assignee = f"{first['assignee']}" if first.get("assignee") else "the team"
        parts.append(f"Action items were assigned, starting with {assignee} to {first['task']}")
    summary = ". ".join(parts)
    if not summary.endswith("."):
        summary += "."
    if len(parts) == 1:
        summary += " Additional follow-ups may be noted in the transcript.";
    return summary


def process_transcript(path: str) -> Dict[str, object]:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines()
    meeting_date = extract_meeting_date(text)
    participants = extract_participants(lines)
    action_items = extract_action_items(lines)
    key_decisions = extract_decisions(lines)
    summary = build_summary(action_items, key_decisions)

    return {
        "meeting_date": meeting_date,
        "participants": participants,
        "action_items": action_items,
        "key_decisions": key_decisions,
        "summary": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract action items and key decisions from a meeting transcript.",
    )
    parser.add_argument("path", help="Path to transcript text/markdown file")
    args = parser.parse_args()

    result = process_transcript(args.path)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
