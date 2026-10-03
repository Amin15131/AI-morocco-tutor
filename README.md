# 🎓 AI Morocco Tutor

AI-powered adaptive learning platform for Moroccan 2BAC Sciences Mathématiques students.

## Features

- Student accounts
- SQLite database
- Adaptive exercise selection
- Math and Physics exercise bank
- Lessons
- AI Tutor with Ollama
- Equation solver
- Derivative calculator
- Integral calculator
- Limit calculator
- Pre-Test / Post-Test
- XP and levels
- Achievement badges
- Student analytics
- CSV learning-data export
- Admin panel
- Exercise management
- Lesson management

## Requirements

- Python 3.10+
- Ollama
- Qwen3 1.7B

## Install

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## AI setup

Install Ollama, then:

```bash
ollama pull qwen3:1.7b
ollama run qwen3:1.7b
```

Keep Ollama running.

## Run

Open another terminal:

```bash
cd C:\Users\LENOVO\AI-morocco-tutor
venv\Scripts\activate
streamlit run app.py
```

Then open:

http://localhost:8501

## Admin

Default admin:

- Username: `admin`
- Password: `admin123`

Change the password before public deployment.

## Project structure

```text
AI-morocco-tutor/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
└── tutor.db              # created automatically
```

## Research direction

The platform is designed to support a learning experiment:

Pre-Test → Adaptive Learning → Post-Test

Possible metrics:

- accuracy improvement
- chapter-level weaknesses
- exercise completion
- AI tutor usage
- pre/post score improvement

For real student testing, collect informed consent and use anonymized data.

## GitHub

```bash
git init
git add .
git commit -m "Initial AI Morocco Tutor release"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```
