# 🤖 Multi-Platform Job Agent

Automatically searches and applies to jobs across **LinkedIn**, **Indeed**, **Internshala**, and **Freelancer.com** every day at **9:00 AM IST** using GitHub Actions.

No laptop needed after setup. Just check your email each morning for the daily report.

---

## 📁 Project Structure

```
multi-job-agent/
├── .github/workflows/
│   └── job_agent.yml          ← GitHub Actions schedule
├── platforms/
│   ├── linkedin/
│   │   ├── browser.py         ← Login + profile visit
│   │   ├── job_search.py      ← Search Easy Apply jobs
│   │   └── job_apply.py       ← Auto Easy Apply
│   ├── indeed/
│   │   ├── browser.py
│   │   ├── job_search.py      ← Search Indeed Apply jobs
│   │   └── job_apply.py       ← Auto apply
│   ├── internshala/
│   │   ├── browser.py
│   │   ├── job_search.py
│   │   └── job_apply.py       ← Apply with cover letter
│   └── freelancer/
│       ├── browser.py
│       ├── job_search.py      ← Search projects
│       └── job_apply.py       ← Auto-bid on projects
├── shared/
│   ├── job_matcher.py         ← AI scoring (free Gemini API)
│   ├── notifier.py            ← Daily email report
│   ├── resume_parser.py       ← Read your PDF resume
│   └── otp_reader.py          ← Reads OTP from Gmail if needed
├── agent_cloud.py             ← Main runner
├── encode_resume.py           ← Run once to encode your PDF
├── config.json                ← Placeholder config (secrets go in GitHub)
├── requirements.txt
└── .gitignore
```

---

## 🗓️ How Phases Activate (Automatic)

| Days Since Start | Phase | What Happens |
|---|---|---|
| Days 1–7   | Phase 1 | Login + profile visit on all enabled platforms |
| Days 8–14  | Phase 2 | + Search jobs + AI match vs your resume (emailed to you, no applying yet) |
| Day 15+    | Phase 3 | + Auto-apply / auto-bid up to daily cap on each platform |

---

## 🔑 STEP 1 — Get a Free Gemini API Key (for AI matching)

1. Go to https://aistudio.google.com/app/apikey
2. Sign in with Google → Click **Create API Key**
3. Copy the key (starts with `AIza...`)
4. Free tier: 1500 requests/day — more than enough

---

## 📄 STEP 2 — Encode Your Resume PDF

Run this once on your PC:

```cmd
python encode_resume.py
```

This creates `resume_base64.txt` — you'll paste its contents as a GitHub Secret.

---

## 📂 STEP 3 — Create a Private GitHub Repository

1. Go to https://github.com → Sign in
2. Click **"+"** → **"New repository"**
3. Name it `multi-job-agent`
4. Set to **Private** ← IMPORTANT
5. Click **"Create repository"**

---

## 💻 STEP 4 — Push Code to GitHub

```cmd
git init
git add .
git commit -m "Multi-Platform Job Agent"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/multi-job-agent.git
git push -u origin main
```

For the password prompt, use a **Personal Access Token**:
- GitHub → Settings → Developer settings → Personal access tokens → Generate new token (classic) → check `repo` → Copy

---

## 🔐 STEP 5 — Add Secrets to GitHub

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add each secret below. Only add the platforms you want to enable:

### Required (all platforms)
| Secret Name | Value |
|---|---|
| `NOTIFY_EMAIL` | Your Gmail address (receives daily reports) |
| `GMAIL_APP_PASSWORD` | 16-char Gmail App Password (see below) |
| `RESUME_PDF_BASE64` | Full contents of `resume_base64.txt` |
| `GEMINI_API_KEY` | From Step 1 (free AI job matching) |

### LinkedIn
| Secret Name | Value |
|---|---|
| `LINKEDIN_EMAIL` | Your LinkedIn login email |
| `LINKEDIN_PASSWORD` | Your LinkedIn password |

### Indeed
| Secret Name | Value |
|---|---|
| `INDEED_EMAIL` | Your Indeed login email |
| `INDEED_PASSWORD` | Your Indeed password |

### Internshala
| Secret Name | Value |
|---|---|
| `INTERNSHALA_EMAIL` | Your Internshala login email |
| `INTERNSHALA_PASSWORD` | Your Internshala password |

### Freelancer
| Secret Name | Value |
|---|---|
| `FREELANCER_EMAIL` | Your Freelancer.com login email |
| `FREELANCER_PASSWORD` | Your Freelancer.com password |

### How to get Gmail App Password:
1. Go to myaccount.google.com → Security
2. Enable **2-Step Verification** (required)
3. Search **"App Passwords"**
4. App: Mail, Device: Other → Generate
5. Copy the 16-character password

---

## ⚙️ STEP 6 — Disable Unwanted Platforms

Open `config.json` and set `"enabled": false` for any platform you don't want:

```json
"internshala": {
  "enabled": false,   ← set false to skip this platform
  ...
}
```

Commit and push the change.

---

## ▶️ STEP 7 — Test It Manually

1. Go to your GitHub repo → **Actions** tab
2. Click **"Multi-Platform Job Agent 🤖"**
3. Click **"Run workflow"**
4. For a full test, set `test_all_phases` to `true`
5. Watch it run (takes ~10-15 minutes for all platforms)
6. ✅ Green = working!

---

## 📧 What Your Daily Email Looks Like

```
MULTI-PLATFORM JOB AGENT — DAILY REPORT
Sunday, 20 April 2026
Phase 3 Active

📊 SUMMARY
  Total Jobs Found   : 62
  Total Good Matches : 14
  Total Applied      : 14

═══════════════════════════════════════════════

💼 LINKEDIN
  Login: ✅  |  Profile: ✅  |  Found: 18  |  Matched: 4  |  Applied: 4

  Top Matches:
    [ 91/100] Java Backend Engineer @ Infosys
               Reason: Strong Java/Spring Boot match, exp aligns
               Link: https://www.linkedin.com/jobs/...

    [ 85/100] Full Stack Developer @ TCS
               Reason: Good React + Java combination
               Link: https://www.linkedin.com/jobs/...

  Applied Today:
    ✅ Java Backend Engineer @ Infosys
    ✅ Full Stack Developer @ TCS

🔵 INDEED
  Login: ✅  |  Profile: ✅  |  Found: 22  |  Matched: 5  |  Applied: 5
  ...

🎓 INTERNSHALA
  Login: ✅  |  Profile: ✅  |  Found: 12  |  Matched: 3  |  Applied: 3
  ...

🧑‍💻 FREELANCER
  Login: ✅  |  Profile: ✅  |  Found: 10  |  Matched: 2  |  Applied: 2
  ...
```

---

## 🛠️ Customizing the Agent

### Change keywords / skills
Edit `config.json`:
```json
"job_search": {
  "keywords": ["Java Developer", "Spring Boot", "Full Stack"],
  "skills":   ["Java", "Spring Boot", "Angular", "SQL"]
}
```

### Change daily application limits (per platform)
```json
"linkedin":    { "max_applications_per_day": 15 },
"indeed":      { "max_applications_per_day": 15 },
"internshala": { "max_applications_per_day": 15 },
"freelancer":  { "max_bids_per_day": 10 }
```

### Change Freelancer bid proposal
```json
"freelancer": {
  "bid_proposal": "Hi! I specialize in Java and Spring Boot with 3+ years of experience..."
}
```

### Change Internshala cover letter
```json
"internshala": {
  "cover_letter": "I am excited to apply for this role..."
}
```

---

## ❓ Troubleshooting

| Problem | Fix |
|---|---|
| LinkedIn login fails with "checkpoint" | LinkedIn requires manual verification — disable LinkedIn or re-login manually to clear the checkpoint |
| Indeed login fails | Try logging in manually and completing any CAPTCHA first |
| No jobs found on a platform | Check that keywords match actual job titles on that platform |
| Freelancer bid fails | Check that your Freelancer account has available bids (free accounts have limited bids/month) |
| AI matching not working | Check `GEMINI_API_KEY` secret is set correctly |
| No email received | Check spam folder; verify `GMAIL_APP_PASSWORD` is correct |
| Resume not loading | Re-run `encode_resume.py` and update `RESUME_PDF_BASE64` secret |
| Action fails on Chrome | Re-run workflow — transient GitHub infrastructure issue |

---

## 🛡️ Security Reminders

- ✅ Repository must be **Private** — never make it public
- ✅ All credentials stored as **GitHub Secrets** — encrypted, never in code
- ✅ `.gitignore` prevents `config.json` and PDFs from being committed
- ❌ Never paste real passwords into `config.json`
- ❌ Never make the repository public
