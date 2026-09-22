"""FastAPI 入口：页面路由 + REST API。"""

import json
import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from . import db
from .analyzer import ManifestError, analyze
from .licenses import POLICIES

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_PATH = os.environ.get(
    "SAMPLE_PATH", os.path.join(BASE_DIR, "..", "sample_manifest.json")
)

app = FastAPI(title="开源依赖许可审查", version="1.0.0")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@app.on_event("startup")
def startup():
    db.init_db()


class ReviewIn(BaseModel):
    policy: str
    manifest: dict


class ExceptionIn(BaseModel):
    package: str
    note: str = ""


# ---------- 页面 ----------

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ---------- 元数据 ----------

@app.get("/api/policies")
def list_policies():
    return [
        {"key": key, "label": p["label"], "description": p["description"]}
        for key, p in POLICIES.items()
    ]


@app.get("/api/sample-manifest")
def sample_manifest():
    try:
        with open(SAMPLE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(404, "示例清单文件不存在")


# ---------- 审查 ----------

@app.post("/api/reviews", status_code=201)
def create_review(payload: ReviewIn):
    try:
        result = analyze(payload.manifest, payload.policy, [])
    except ManifestError as e:
        raise HTTPException(400, str(e))
    review_id = db.create_review(
        payload.policy, result["project"]["name"], payload.manifest, result
    )
    return db.get_review(review_id)


@app.get("/api/reviews")
def list_reviews():
    return db.list_reviews()


@app.get("/api/reviews/{review_id}")
def get_review(review_id: int):
    review = db.get_review(review_id)
    if review is None:
        raise HTTPException(404, "审查记录不存在")
    return review


def _recalculate(review_id: int):
    review = db.get_review(review_id)
    if review is None:
        raise HTTPException(404, "审查记录不存在")
    exception_names = [e["package"] for e in review["exceptions"]]
    result = analyze(review["manifest"], review["policy"], exception_names)
    db.update_result(review_id, result)
    return db.get_review(review_id)


@app.post("/api/reviews/{review_id}/recalculate")
def recalculate(review_id: int):
    return _recalculate(review_id)


# ---------- 例外包 ----------

@app.post("/api/reviews/{review_id}/exceptions", status_code=201)
def add_exception(review_id: int, payload: ExceptionIn):
    review = db.get_review(review_id)
    if review is None:
        raise HTTPException(404, "审查记录不存在")
    known = {f["package"] for f in review["result"]["findings"]}
    if payload.package not in known:
        raise HTTPException(400, f"包 {payload.package} 不在本次审查的依赖清单中")
    db.add_exception(review_id, payload.package, payload.note)
    return _recalculate(review_id)


@app.delete("/api/reviews/{review_id}/exceptions/{package}")
def remove_exception(review_id: int, package: str):
    review = db.get_review(review_id)
    if review is None:
        raise HTTPException(404, "审查记录不存在")
    db.remove_exception(review_id, package)
    return _recalculate(review_id)


# ---------- 导出 ----------

@app.get("/api/reviews/{review_id}/export")
def export_review(review_id: int):
    review = db.get_review(review_id)
    if review is None:
        raise HTTPException(404, "审查记录不存在")
    result = review["result"]
    payload = {
        "tool": "license-review",
        "exported_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "review_id": review_id,
        "project": result["project"],
        "policy": result["policy"],
        "policy_label": result["policy_label"],
        "exceptions": review["exceptions"],
        "summary": result["summary"],
        "findings": result["findings"],
    }
    filename = f"license-review-{review_id}.json"
    return JSONResponse(
        payload,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
