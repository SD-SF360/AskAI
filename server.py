from flask import Flask,jsonify,request
from flask_cors import CORS
import random
import os

from feed_engine import generate_feed
from stats_engine import answer_question


app=Flask(__name__)

CORS(app)

app.register_blueprint(daily_challenge)  # ✅ NEW


@app.route("/")
def home():
    return {"status":"SportsFan360 AI running"}


# ---------------- FEED ----------------

@app.route("/feed")
def feed():

    try:
        data=generate_feed()
        return jsonify(data)

    except Exception as e:

        return jsonify({
            "cards":[
                {
                    "type":"question",
                    "title":"Trending Question",
                    "text":"Highest IPL score"
                },
                {
                    "type":"insight",
                    "title":"AI Insight",
                    "text":"Teams defending totals win slightly more night games."
                },
                {
                    "type":"stat",
                    "title":"Stat Highlight",
                    "text":"Virat Kohli is the all-time leading IPL run scorer."
                }
            ]
        })


# ---------------- ASK AI ----------------

@app.route("/ask")
def ask():

    q=request.args.get("question","")

    try:
        result=answer_question(q)
        return jsonify(result)

    except Exception as e:

        return jsonify({
            "answer":"Unable to analyze IPL data currently",
            "chart_data":[]
        })


# ---------------- TRIVIA ----------------

def generate_trivia():

    questions=[ ... ]  # keep same

    random.shuffle(questions)

    return {"questions":questions}


@app.route("/trivia")
def trivia():
    return jsonify(generate_trivia())


# ---------------- SERVER ----------------

if __name__=="__main__":

    port=int(os.environ.get("PORT",8000))

    app.run(
        host="0.0.0.0",
        port=port
    )