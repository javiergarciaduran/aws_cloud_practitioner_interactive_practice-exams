
#!/usr/bin/env python3
"""
Interactive multiple-choice exam runner for Markdown exams (GitHub pipeline) — refined UI.

Changes:
- Removes any '<details ...>...</details>' blocks and any '&lt;...&gt;' fragments from question text.
- No '(Original #N)' in the question header.
- Prompt shows just 'Select your answer:' (no examples), even for multi-select.
- After each question, prints running score as 'correct/total' (no percentage).
- Explanations are never shown.

GitHub source:
  Repo:  kananinirav/AWS-Certified-Cloud-Practitioner-Notes
  Dir:   practice-exam
  Branch: master

Examples:
  python mcq_exam.py --source github --exam-number 16 --shuffle-questions --shuffle-choices
  python mcq_exam.py --source local --exam-md practice-exam-16.md
"""
import re
import sys
import argparse
import random
from pathlib import Path

try:
    import requests  # for GitHub fetch
except ImportError:
    requests = None

# --- Regex patterns for parsing ---
CHOICE_RE = re.compile(r"^\s*-\s*([A-Z])\.\s*(.*)")
QUESTION_RE = re.compile(r"^\s*(\d+)\.\s+(.*)")
CORRECT_RE = re.compile(r"Correct\s+Answer:\s*([A-Z]+)", re.IGNORECASE)
CHOOSE_RE = re.compile(r"\(\s*Choose\s+(one|two|three|four|five)\.?\s*\)", re.IGNORECASE)

WORD_TO_INT = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5}

REPO_USER   = "kananinirav"
REPO_NAME   = "AWS-Certified-Cloud-Practitioner-Notes"
REPO_BRANCH = "master"
REPO_EXAMS_DIR = "practice-exam"

# --- Cleaning helpers ---------------------------------------------------------

DETAILS_ENTITY_BLOCK_RE = re.compile(r"&lt;details[\s\S]*?&lt;/details&gt;", re.IGNORECASE)
ANGLE_ENTITY_RE         = re.compile(r"&lt;[^&]*?&gt;")
DETAILS_HTML_BLOCK_RE   = re.compile(r"<details[\s\S]*?</details>", re.IGNORECASE)
ANY_HTML_TAG_RE         = re.compile(r"<[^>]+>")

def clean_question_text(text: str) -> str:
    """
    Remove details/HTML fragments that sometimes appear inline in the repo questions:
    - &lt;details ...&gt; ... &lt;/details&gt;   (escaped entities)
    - Any remaining &lt;...&gt;
    - <details ...>...</details>           (actual HTML, por si acaso)
    - Any remaining <...> tags
    Then collapse extra whitespace.
    """
    if not text:
        return text

    # Remove encoded <details> blocks first
    text = DETAILS_ENTITY_BLOCK_RE.sub("", text)
    # Remove any other &lt;...&gt; fragments
    text = ANGLE_ENTITY_RE.sub("", text)
    # Remove actual HTML <details> blocks
    text = DETAILS_HTML_BLOCK_RE.sub("", text)
    # Remove any remaining HTML tags
    text = ANY_HTML_TAG_RE.sub("", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

# --- Model --------------------------------------------------------------------

class Question:
    def __init__(self, number, text):
        self.number = number
        self.text = text.strip()
        self.choices = []              # list[tuple(letter, text)]
        self.correct_letters = []      # list[str]
        self.choose_n = None           # int | None

    def add_choice(self, letter, text):
        self.choices.append((letter.upper(), text.strip()))

    def set_correct(self, letters):
        self.correct_letters = [ch.upper() for ch in letters]

    def infer_choose_n(self):
        if self.choose_n is None and self.correct_letters:
            self.choose_n = len(self.correct_letters)

# --- Source acquisition --------------------------------------------------------

def build_github_raw_url(exam_number: int) -> str:
    filename = f"practice-exam-{exam_number}.md"
    path_in_repo = f"{REPO_EXAMS_DIR}/{filename}"
    return f"https://raw.githubusercontent.com/{REPO_USER}/{REPO_NAME}/{REPO_BRANCH}/{path_in_repo}"

def fetch_exam_from_github(exam_number: int) -> str:
    if requests is None:
        raise RuntimeError("The 'requests' package is required for --source github. "
                           "Install it with: python -m pip install requests")
    url = build_github_raw_url(exam_number)
    resp = requests.get(url, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch exam {exam_number} (HTTP {resp.status_code}). URL: {url}")
    return resp.text

def read_local_exam(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path.read_text(encoding='utf-8', errors='ignore')

# --- Parser -------------------------------------------------------------------

def parse_markdown_exam_text(text: str):
    """
    Parse Markdown into a list of Question objects.
    - Ignores preamble/front matter.
    - Wraps question lines into the question text.
    - 'Answer Correct Answer: X' may appear after choices.
    """
    questions = []
    current_q = None

    lines = text.splitlines()
    for line in lines:
        # New question?
        qmatch = QUESTION_RE.match(line)
        if qmatch:
            # finalize previous
            if current_q:
                current_q.infer_choose_n()
                # Clean question text before storing
                current_q.text = clean_question_text(current_q.text)
                questions.append(current_q)

            number = int(qmatch.group(1))
            qtext  = qmatch.group(2)
            current_q = Question(number, qtext)

            # Detect "(Choose ...)"
            cm = CHOOSE_RE.search(qtext)
            if cm:
                word = cm.group(1).lower()
                current_q.choose_n = WORD_TO_INT.get(word)
            continue

        if current_q is None:
            continue

        # Choice
        cmatch = CHOICE_RE.match(line)
        if cmatch:
            letter, text_opt = cmatch.groups()
            current_q.add_choice(letter, text_opt)
            continue

        # Correct answer
        rmatch = CORRECT_RE.search(line)
        if rmatch:
            letters = list(rmatch.group(1).strip())
            current_q.set_correct(letters)
            current_q.infer_choose_n()
            continue

        # Wrapped question text (avoid 'Answer' and choices)
        if line and not line.startswith('-') and not line.strip().startswith('Answer'):
            current_q.text += ' ' + line.strip()

    # finalize last
    if current_q and current_q.choices:
        current_q.infer_choose_n()
        current_q.text = clean_question_text(current_q.text)
        questions.append(current_q)

    # keep only well-formed questions
    questions = [q for q in questions if q.choices]
    return questions

# --- Runner -------------------------------------------------------------------

def run_quiz(questions, shuffle_questions=False, shuffle_choices=False, limit=None, seed=None):
    if seed is not None:
        random.seed(seed)
    if shuffle_questions:
        random.shuffle(questions)
    if limit is not None:
        questions = questions[:limit]

    correct = 0
    total = len(questions)
    running_total = 0

    for idx, q in enumerate(questions, 1):
        # Header without "(Original #N)"
        running_total += 1
        print(f"\nQuestion {idx} of {total}")
        print(q.text)

        choices = list(q.choices)
        if shuffle_choices:
            random.shuffle(choices)

        for letter, text in choices:
            print(f"  {letter}. {text}")

        q.infer_choose_n()
        multi = (q.choose_n and q.choose_n > 1) or len(q.correct_letters) > 1
        # Prompt without examples, even for multi-select
        prompt = "Select your answer: "

        # Read/validate user input
        while True:
            try:
                raw = input(prompt).strip()
            except EOFError:
                print("\nInput closed.")
                return
            # Extract letters (accepts formats like 'BD' or 'B,D')
            letters = [ch.upper() for ch in re.findall(r"[A-Za-z]", raw)]
            if not letters:
                print("Please enter at least one letter.")
                continue

            valid_letters = {l for (l, _) in choices}
            if not set(letters).issubset(valid_letters):
                invalid = sorted(set(letters) - valid_letters)
                print(f"Invalid option(s): {', '.join(invalid)}. Try again.")
                continue

            if multi:
                expected_n = q.choose_n or len(q.correct_letters)
                if len(set(letters)) != expected_n:
                    print(f"Please select exactly {expected_n} unique letter(s).")
                    continue
                is_correct = set(letters) == set(q.correct_letters)
            else:
                is_correct = letters[0] == q.correct_letters[0]
            break

        if is_correct:
            print("✅ Correct!")
            correct += 1
        else:
            print("❌ Incorrect.")
            corr_texts = {l: t for (l, t) in choices}
            corr_info = ", ".join([f"{l}. {corr_texts.get(l, '')}" for l in q.correct_letters])
            print(f"Correct answer: {corr_info}")

        # Running score 
        print(f"Score: {correct}/{running_total}")

    # Final score 
    print(f"\nYour final score: {correct}/{total}")
    
    final_score = correct/total
    if final_score >= 0.7:
        print(f"\nCongratulations! You have passed the exam with a score of {final_score*100}/100")
    else:
        print(f"\nSorry, you have not passed the exam. Good luck for the next one!")

# --- CLI ----------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description='Interactive multiple-choice exam runner for Markdown exams (GitHub pipeline).'
    )
    ap.add_argument('--source', choices=['github', 'local'], required=True,
                    help='Where to load the exam from: github (download) or local (file path)')
    ap.add_argument('--exam-number', type=int, default=None,
                    help='Exam number to fetch from GitHub (e.g., 16 => practice-exam-16.md)')
    ap.add_argument('--exam-md', type=str, default=None,
                    help='Local Markdown file path (required if --source local)')
    ap.add_argument('--shuffle-questions', action='store_true',
                    help='Shuffle question order')
    ap.add_argument('--shuffle-choices', action='store_true',
                    help='Shuffle choices within each question')
    ap.add_argument('--limit', type=int, default=None,
                    help='Limit to the first N questions after optional shuffle')
    ap.add_argument('--seed', type=int, default=None,
                    help='Random seed for reproducibility when shuffling')

    args = ap.parse_args()

    # Acquire Markdown text
    if args.source == 'github':
        if args.exam_number is None:
            print("Please provide --exam-number when --source github.")
            sys.exit(2)
        try:
            md_text = fetch_exam_from_github(args.exam_number)
        except Exception as e:
            print(f"Error fetching exam from GitHub: {e}")
            sys.exit(3)
    else:
        if not args.exam_md:
            print("Please provide --exam-md when --source local.")
            sys.exit(2)
        try:
            md_text = read_local_exam(Path(args.exam_md))
        except Exception as e:
            print(f"Error reading local file: {e}")
            sys.exit(3)

    # Parse and run
    questions = parse_markdown_exam_text(md_text)
    if not questions:
        print("No questions found. Please verify the Markdown format.")
        sys.exit(4)

    run_quiz(
        questions,
        shuffle_questions=args.shuffle_questions,
        shuffle_choices=args.shuffle_choices,
        limit=args.limit,
        seed=args.seed,
    )

if __name__ == '__main__':
    main()
