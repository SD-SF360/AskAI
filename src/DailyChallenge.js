import React, { useState, useEffect } from "react";

function DailyChallenge({ match, API_URL }) {

  const [prediction, setPrediction] = useState(null);
  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);

  const matchId = match?.id || `${match?.team1}-${match?.team2}`;

  useEffect(() => {
    fetch(`${API_URL}/daily-challenge?matchId=${matchId}`)
      .then(res => res.json())
      .then(data => setPrediction(data))
      .catch(() => setPrediction(null));
  }, [matchId]);

  useEffect(() => {
    const saved = localStorage.getItem("ipl_prediction");

    if (saved) {
      const parsed = JSON.parse(saved);
      if (parsed.matchId === matchId) {
        setAnswers(parsed.answers || {});
        setSubmitted(true);
      }
    }
  }, [matchId]);

  const handleSelect = (qId, option) => {

    if (submitted) return;

    const updated = { ...answers, [qId]: option };
    setAnswers(updated);

    // 🔥 AUTO NEXT STEP
    setTimeout(() => {
      if (currentStep < prediction.questions.length - 1) {
        setCurrentStep(currentStep + 1);
      }
    }, 300);
  };

  const handleSubmit = () => {

    localStorage.setItem("ipl_prediction", JSON.stringify({
      matchId,
      answers,
      submittedAt: Date.now()
    }));

    setSubmitted(true);
  };

  if (!prediction || !match) return null;

  const q = prediction.questions[currentStep];

  return (
    <div className="challengeCard">

      <h3>🔥 Daily IPL Challenge</h3>

      <p className="challengeHint">
        Predict smart. You can submit only once. No edits after submission.
      </p>

      <p className="matchTitle">
        {match.team1} vs {match.team2}
      </p>

      {!submitted ? (

        <div className="stepCard fadeSlide">

          <div className="progressBar">
            <div
              className="progressFill"
              style={{ width: `${((currentStep + 1) / prediction.questions.length) * 100}%` }}
            />
          </div>

          <p className="questionText">{q.question}</p>

          <div className="options">
            {q.options.map((opt, i) => (
              <button
                key={i}
                className={answers[q.id] === opt ? "optionBtn selected" : "optionBtn"}
                onClick={() => handleSelect(q.id, opt)}
              >
                {opt}
              </button>
            ))}
          </div>

          {currentStep === prediction.questions.length - 1 && (
            <button className="submitBtn" onClick={handleSubmit}>
              Submit Predictions 🚀
            </button>
          )}

        </div>

      ) : (

        <div className="successCard fadeSlide">

          <h4>🎉 Thanks for participating!</h4>

          <p>
            Your predictions are locked in.
          </p>

          <p className="subText">
            Come back after the match to see how you performed 🔥
          </p>

        </div>

      )}

    </div>
  );
}

export default DailyChallenge;