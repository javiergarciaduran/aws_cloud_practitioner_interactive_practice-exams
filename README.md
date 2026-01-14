# AWS Practice Exam Runner

An interactive command-line tool for taking AWS Certified Cloud Practitioner practice exams. Questions are sourced from the excellent [AWS-Certified-Cloud-Practitioner-Notes](https://github.com/kananinirav/AWS-Certified-Cloud-Practitioner-Notes) repository by kananinirav.

## Features

- Interactive multiple-choice exam experience
- Support for single and multi-select questions
- Immediate feedback on answers
- Running score tracking
- Optional question/answer shuffling for varied practice
- Fetch exams directly from GitHub or use local files

## Requirements

- Python 3.6+
- `requests` library (for GitHub fetching)

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install requests
```

## Usage

### Fetch exam from GitHub
```bash
python mcq_exam.py --source github --exam-number 16
```

### With shuffling options
```bash
python mcq_exam.py --source github --exam-number 16 --shuffle-questions --shuffle-choices
```

### Use a local exam file
```bash
python mcq_exam.py --source local --exam-md practice-exam-16.md
```

### Additional options
```bash
python mcq_exam.py --source github --exam-number 16 --limit 10 --seed 42
```

## Command-line Arguments

- `--source {github,local}` - Where to load the exam from (required)
- `--exam-number N` - Exam number to fetch from GitHub (1-65+)
- `--exam-md PATH` - Local Markdown file path (required if --source local)
- `--shuffle-questions` - Randomize question order
- `--shuffle-choices` - Randomize answer choices
- `--limit N` - Practice with only the first N questions
- `--seed N` - Set random seed for reproducible shuffling

## Passing Score

You need 70% or higher to pass the practice exam.

## Credits

Practice exams are sourced from [kananinirav/AWS-Certified-Cloud-Practitioner-Notes](https://github.com/kananinirav/AWS-Certified-Cloud-Practitioner-Notes).
