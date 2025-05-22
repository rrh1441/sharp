from fastapi import FastAPI
from worker import _process, _body, gmail, _new_msgs, _load_hist

app = FastAPI()


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.post("/run-once")
def run_once():
    msgs = _new_msgs(_load_hist())
    for m in msgs:
        _process(_body(m["id"]))
    return {"processed": len(msgs)}