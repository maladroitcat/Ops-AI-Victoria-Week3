# Operationalizing AI

Welcome to the course. This repository has all the code, data, and assignments for weeks 1–7.

Check Canvas for deadlines, submission policies, and grading rubrics. Everything else is here.

## The Course

You're building two complete systems that both fail. You'll have to diagnose and fix them.

**Weeks 1–4: Taxi Demand Forecasting.** A model predicts how many taxi trips will happen in each NYC neighborhood in the next 15 minutes. You deploy it to production. It works for a few weeks, then the real world changes and it breaks. You learn deployment (Kubernetes), validation (data quality), monitoring (detecting failures), and recovery (retraining without breaking things).

**Weeks 5–7: TechCorp LLM Agent.** An AI assistant answers questions about company policy, benefits, employee data. First it works. Then access control breaks it—some people shouldn't see certain documents. Then it gets expensive and slow. You learn to build systems with real constraints: cost, access control, data quality, accuracy.

Each week builds on the previous one. By the end you've shipped two systems and learned what actually matters in production.

## Getting Started

Clone this repo. Everything you need is in each week folder.

```bash
git clone https://github.com/AkhilByteWrangler/Ops-AI-Student-View.git
cd Ops-AI-Student-View

# Install Git LFS (for data files)
brew install git-lfs
git lfs install
git lfs pull

# Read Week 1
cd week1 && cat README.md
```

Each week has:
- A README with the assignment
- A READING.md with background
- Data files
- Starter code templates

## Important

**Check Canvas for:**
- Exact deadlines for each week
- Submission instructions
- Grading rubrics
- Late policy

All due dates and policies are on Canvas, not here. The assignments are here. Canvas is the source of truth for timelines.

Start with week1/README.md. Read it. Do it. Submit on time.
