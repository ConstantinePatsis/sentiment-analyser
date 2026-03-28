import os
import json
from flask import Flask, request, jsonify
import anthropic

app = Flask(__name__)
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

HTML = """<!DOCTYPE html>
<html>
<head>
<title>SentimentIQ</title>
<style>
body{font-family:sans-serif;max-width:800px;margin:40px auto;padding:20px;background:#0a0a0a;color:#f0f0f0}
h1{font-size:32px;margin-bottom:8px}h1 span{color:#ff6b35}
p{color:#666;margin-bottom:24px}
textarea{width:100%;height:200px;background:#111;border:1px solid #333;border-radius:8px;padding:16px;color:#f0f0f0;font-size:14px;resize:vertical}
button{width:100%;padding:16px;background:#ff6b35;color:#000;border:none;border-radius:8px;font-size:16px;font-weight:700;cursor:pointer;margin-top:12px}
button:disabled{opacity:0.4}
#status{text-align:center;color:#666;padding:16px;display:none}
#results{margin-top:32px;display:none}
.card{background:#111;border:1px solid #222;border-radius:8px;padding:20px;margin-bottom:16px}
.label{font-size:11px;color:#ff6b35;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px}
.score{font-size:48px;font-weight:800;color:#ff6b35}
li{padding:6px 0;border-bottom:1px solid #222;color:#bbb;font-size:14px}
li:last-child{border-bottom:none}
.quote{border-left:2px solid #ff6b35;padding:8px 12px;margin:8px 0;color:#ccc;font-style:italic;font-size:13px}
</style>
</head>
<body>
<h1>Sentiment<span>IQ</span></h1>
<p>Paste customer reviews — one per line. Get instant AI analysis.</p>
<textarea id="reviews" placeholder="The room was clean and staff were helpful..."></textarea>
<button id="btn" onclick="analyse()">Analyse reviews →</button>
<div id="status">Analysing with Claude...</div>
<div id="results">
  <div class="card">
    <div class="label">Overall score</div>
    <div class="score" id="score"></div>
    <div id="sentiment"></div>
  </div>
  <div class="card">
    <div class="label">Summary</div>
    <div id="summary"></div>
  </div>
  <div class="card">
    <div class="label">What people love</div>
    <ul id="positives"></ul>
  </div>
  <div class="card">
    <div class="label">What people complain about</div>
    <ul id="negatives"></ul>
  </div>
  <div class="card">
    <div class="label">Recommendations</div>
    <ul id="recommendations"></ul>
  </div>
  <div class="card">
    <div class="label">Notable quotes</div>
    <div id="quotes"></div>
  </div>
</div>
<script>
async function analyse(){
  const reviews=document.getElementById('reviews').value.trim();
  if(!reviews){alert('Paste some reviews first');return}
  document.getElementById('btn').disabled=true;
  document.getElementById('status').style.display='block';
  document.getElementById('results').style.display='none';
  try{
    const res=await fetch('/analyse',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reviews})});
    const json=await res.json();
    if(json.error)throw new Error(json.error);
    const d=json.data;
    document.getElementById('score').textContent=Math.round((d.sentiment_score||0.5)*100)+'%';
    document.getElementById('sentiment').textContent=d.overall_sentiment;
    document.getElementById('summary').textContent=d.summary;
    document.getElementById('positives').innerHTML=(d.top_positives||[]).map(p=>`<li>${p}</li>`).join('');
    document.getElementById('negatives').innerHTML=(d.top_negatives||[]).map(n=>`<li>${n}</li>`).join('');
    document.getElementById('recommendations').innerHTML=(d.recommendations||[]).map(r=>`<li>${r}</li>`).join('');
    document.getElementById('quotes').innerHTML=(d.notable_quotes||[]).map(q=>`<div class="quote">"${q}"</div>`).join('');
    document.getElementById('results').style.display='block';
  }catch(err){alert('Error: '+err.message)}
  finally{document.getElementById('btn').disabled=false;document.getElementById('status').style.display='none'}
}
</script>
</body>
</html>"""

PROMPT = """Analyse these reviews and return ONLY valid JSON:
{{
  "overall_sentiment": "positive|negative|neutral|mixed",
  "sentiment_score": 0.0-1.0,
  "total_reviews": {count},
  "summary": "2-3 sentence summary",
  "top_positives": ["5 things people love"],
  "top_negatives": ["5 things people complain about"],
  "recommendations": ["3-5 actionable recommendations"],
  "notable_quotes": ["3 representative quotes"]
}}

Reviews:
{reviews}"""

@app.route("/")
def index():
    return HTML

@app.route("/analyse", methods=["POST"])
def analyse():
    data = request.json
    reviews = data.get("reviews", "")
    count = len([r for r in reviews.split("\n") if r.strip()])
    try:
        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": PROMPT.format(reviews=reviews, count=count)}]
        )
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return jsonify({"success": True, "data": json.loads(raw)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5001)
