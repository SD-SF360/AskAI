import random
import os
import json
from groq import Groq
from stats_engine import runs_cache,wickets_cache,sixes_cache,titles_cache,highest_score_cache
from cricinfo_scraper import get_ipl_points_table

groq = Groq(api_key=os.getenv("GROQ_API_KEY"))


def random_options(correct, pool):

    pool = list(set(pool) - {correct})

    if len(pool) >= 3:
        opts = random.sample(pool,3)
    else:
        opts = pool

    opts.append(correct)
    random.shuffle(opts)

    return opts


# ---------------- DATASET QUESTIONS ----------------

def dataset_questions():

    questions = []

    if runs_cache:

        top = max(runs_cache, key=runs_cache.get)

        questions.append({
            "q":"Who has scored the most runs in IPL history?",
            "options":random_options(top,list(runs_cache.keys())),
            "answer":top
        })

    if wickets_cache:

        top = max(wickets_cache, key=wickets_cache.get)

        questions.append({
            "q":"Who has taken the most wickets in IPL history?",
            "options":random_options(top,list(wickets_cache.keys())),
            "answer":top
        })

    if sixes_cache:

        top = max(sixes_cache, key=sixes_cache.get)

        questions.append({
            "q":"Which player has hit the most sixes in IPL history?",
            "options":random_options(top,list(sixes_cache.keys())),
            "answer":top
        })

    if titles_cache:

        top = max(titles_cache, key=titles_cache.get)

        questions.append({
            "q":"Which team has won the most IPL titles?",
            "options":random_options(top,list(titles_cache.keys())),
            "answer":top
        })

    if highest_score_cache.get("player"):

        p = highest_score_cache["player"]

        questions.append({
            "q":"Who scored the highest individual IPL score?",
            "options":random_options(p,list(runs_cache.keys())),
            "answer":p
        })

    return questions


# ---------------- POINTS TABLE QUESTIONS ----------------

def table_questions():

    questions = []

    try:

        table = get_ipl_points_table()

        if table:

            leader = table[0]["team"]

            teams = [t["team"] for t in table]

            questions.append({
                "q":"Which team is currently leading the IPL points table?",
                "options":random_options(leader,teams),
                "answer":leader
            })

    except:
        pass

    return questions


# ---------------- AI QUESTIONS ----------------

def ai_questions():

    questions = []

    prompt = """
Create ONE IPL trivia question.

Return JSON format only:

{
 "q":"question",
 "options":["A","B","C","D"],
 "answer":"correct option"
}
"""

    try:

        res = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":prompt}],
            temperature=0.7
        )

        text = res.choices[0].message.content
        q = json.loads(text)

        questions.append(q)

    except:
        pass

    return questions


# ---------------- MASTER GENERATOR ----------------

def generate_trivia_questions():

    questions = []

    questions += dataset_questions()
    questions += table_questions()
    questions += ai_questions()

    if not questions:
        return {"questions":[]}

    while len(questions) < 10:

        questions.append(random.choice(questions))

    random.shuffle(questions)

    return {"questions":questions[:10]}