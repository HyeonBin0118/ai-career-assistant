"""AI Career Assistant - 배포용 Streamlit 앱 (음성 기능 제외)"""

import streamlit as st
import os
import time
import json
import requests
from openai import OpenAI

# EC2 API 서버 주소
API_BASE = "http://43.200.8.205:8000/api/v1"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ──────────────────────────────────────────────
# API 공통 함수
# ──────────────────────────────────────────────

def api_post(endpoint: str, **kwargs) -> dict:
    """FastAPI POST 요청 공통 함수"""
    try:
        res = requests.post(f"{API_BASE}/{endpoint}", **kwargs)
        return res.json()
    except Exception as e:
        return {"error": str(e)}


def api_get(endpoint: str) -> dict:
    """FastAPI GET 요청 공통 함수"""
    try:
        res = requests.get(f"{API_BASE}/{endpoint}")
        return res.json()
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# 사이드바
# ──────────────────────────────────────────────

def render_sidebar() -> str:
    """사이드바 렌더링. 선택된 페이지 반환."""
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center; padding: 10px 0;">
            <div style="font-size:2rem;">🤖</div>
            <div style="font-size:1.1rem; font-weight:700; color:white; margin-top:8px;">AI Career Assistant</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("**📌 메뉴**")
        page = st.radio(
            "메뉴",
            ["🏠 홈", "📝 자소서 작성", "🎤 면접 연습", "📋 연습 기록"],
            label_visibility="collapsed",
        )
    return page


# ──────────────────────────────────────────────
# 페이지: 홈
# ──────────────────────────────────────────────

def show_home():
    """홈 화면"""
    st.title("🤖 AI Career Assistant")
    st.markdown("채용공고 분석부터 자소서 작성, 면접 연습까지 한 세션에서.")
    st.divider()

    st.markdown("### 📝 자소서 작성")
    st.markdown("""
- 채용공고 URL + 이력서 입력 → 맞춤형 자소서 자동 생성
- 길이/형식 커스터마이징 가능
- 구체성/직무연관성/구조 항목으로 품질 평가
""")
    st.divider()

    st.markdown("### 🎤 면접 연습")
    st.markdown("""
- 공고 기반 맞춤 질문 8개 자동 생성
- 보유 스킬 심화 / 부족 스킬 / 직무 / 인성 카테고리 구성
- 텍스트 답변 후 논리성/구체성 항목별 점수 + 모범 답안 제공
- 면접 완료 후 카테고리별 평균 점수 리포트
""")
    st.divider()

    st.info("💡 추천 흐름: 자소서 작성 → 면접 연습 → 연습 기록 확인")


# ──────────────────────────────────────────────
# 페이지: 자소서 작성
# ──────────────────────────────────────────────

def show_cover_letter():
    """자소서 생성 및 품질 평가 페이지"""
    st.title("📝 자소서 작성")

    if "cover_state" not in st.session_state:
        st.session_state.cover_state = "input"
        st.session_state.cover_session_id = None
        st.session_state.cover_letter = None

    if st.session_state.cover_state == "input":
        job_url = st.text_input("채용공고 URL", placeholder="https://www.jobkorea.co.kr/...")
        resume_text = st.text_area("이력서 텍스트", placeholder="이력서를 붙여넣으세요...", height=150)

        col1, col2 = st.columns([3, 1])
        with col1:
            length = st.slider("자소서 길이", 200, 1000, 500, step=100)
        with col2:
            st.markdown(f"<br><b>{length}자</b>", unsafe_allow_html=True)

        custom_format = st.text_area(
            "커스텀 형식 (선택)",
            placeholder="비워두면 기본 형식으로 생성됩니다.\n예시:\n1. 지원동기\n2. 직무 관련 경험\n3. 입사 후 포부",
            height=100,
        )

        if st.button("자소서 생성", disabled=not (job_url and resume_text)):
            with st.spinner("자소서 생성 중... (30초 정도 걸려요)"):
                session_data = api_post("sessions", json={"job_url": job_url, "resume_text": resume_text})
                if "id" not in session_data:
                    st.error(f"세션 생성 실패: {session_data}")
                    return
                st.session_state.cover_session_id = session_data["id"]
                cover_data = api_post("cover-letter/generate", json={
                    "session_id": st.session_state.cover_session_id,
                    "length": length,
                    "custom_format": custom_format,
                })
                if "error" in cover_data:
                    st.error(f"자소서 생성 실패: {cover_data['error']}")
                    return
                st.session_state.cover_letter = cover_data["cover_letter"]
                st.session_state.cover_state = "result"
                st.rerun()

    elif st.session_state.cover_state == "result":
        st.markdown("✏️ 각 항목을 직접 수정할 수 있습니다.")
        edited = {}
        for key, value in st.session_state.cover_letter.items():
            edited[key] = st.text_area(key, value=value, height=120, key=f"cover_{key}")
        st.session_state.cover_letter = edited

        st.divider()
        if st.button("📊 품질 평가 받기"):
            with st.spinner("평가 중..."):
                eval_data = api_post("cover-letter/evaluate", json={
                    "session_id": st.session_state.cover_session_id,
                    "cover_letter": st.session_state.cover_letter,
                })
                if "error" not in eval_data:
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("구체성", f"{eval_data.get('specificity', 0)}/10")
                    col2.metric("직무연관성", f"{eval_data.get('relevance', 0)}/10")
                    col3.metric("구조/논리", f"{eval_data.get('structure', 0)}/10")
                    col4.metric("총점", f"{eval_data.get('total', 0)}/30")
                    st.info(f"💬 {eval_data.get('feedback', '')}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 다시 작성"):
                st.session_state.cover_state = "input"
                st.rerun()
        with col2:
            if st.button("🎤 이 자소서로 면접 보기 →"):
                st.session_state.text_session_id = st.session_state.cover_session_id
                st.session_state.text_from_cover = True
                st.session_state.text_state = "questions"
                session_data = api_get(f"sessions/{st.session_state.cover_session_id}")
                st.session_state.text_questions = session_data.get("questions", [])
                st.session_state.text_current_idx = 0
                st.rerun()


# ──────────────────────────────────────────────
# 페이지: 면접 연습
# ──────────────────────────────────────────────

def show_text_interview():
    """텍스트 기반 면접 페이지"""
    st.title("🎤 면접 연습")

    if "text_state" not in st.session_state:
        st.session_state.text_state = "setup"
        st.session_state.text_session_id = None
        st.session_state.text_questions = []
        st.session_state.text_current_idx = 0
        st.session_state.text_from_cover = False

    if st.session_state.text_state == "setup":
        job_url = st.text_input("채용공고 URL", placeholder="https://www.jobkorea.co.kr/...")
        resume_text = st.text_area("이력서 텍스트", placeholder="이력서를 붙여넣으세요...", height=150)

        if st.button("면접 시작", disabled=not (job_url and resume_text)):
            with st.spinner("공고 분석 및 질문 생성 중... (30초 정도 걸려요)"):
                session_data = api_post("sessions", json={"job_url": job_url, "resume_text": resume_text})
                if "error" in session_data:
                    st.error(f"오류: {session_data['error']}")
                    return
                st.session_state.text_session_id = session_data["id"]
                st.session_state.text_questions = session_data.get("questions", [])
                st.session_state.text_current_idx = 0
                st.session_state.text_state = "questions"
                st.rerun()

    elif st.session_state.text_state == "questions":
        questions = st.session_state.text_questions
        idx = st.session_state.text_current_idx

        if idx >= len(questions):
            st.session_state.text_state = "report"
            st.rerun()
            return

        q = questions[idx]
        st.markdown(f"**{idx + 1} / {len(questions)}**")
        st.progress(idx / len(questions))

        category_colors = {"보유 스킬": "🟢", "부족 스킬": "🔴", "직무/회사": "🔵", "인성/경험": "🟡"}
        badge = category_colors.get(q.get("category", ""), "⚪")
        st.markdown(f"{badge} **{q.get('category', '')}**")
        st.info(q.get("question_text", ""))

        direct_text = st.text_area("답변을 입력하세요", height=100, placeholder="질문에 대한 답변을 입력하세요...")
        if st.button("제출"):
            if direct_text.strip():
                with st.spinner("평가 중..."):
                    result = api_post("evaluate-text", json={
                        "question_id": q["id"],
                        "answer_text": direct_text.strip(),
                        "duration_seconds": 0,
                    })
                if "error" not in result:
                    st.session_state.text_feedback = result
                    st.rerun()
                else:
                    st.error(f"평가 실패: {result['error']}")
            else:
                st.warning("답변을 입력해주세요.")

        if "text_feedback" in st.session_state:
            feedback = st.session_state.text_feedback
            st.divider()
            st.markdown("### 📊 답변 평가")
            col1, col2, col3 = st.columns(3)
            col1.metric("논리성", f"{feedback.get('logic_score', 0)}/5")
            col2.metric("구체성", f"{feedback.get('specificity_score', 0)}/5")
            col3.metric("총점", f"{feedback.get('total_score', 0)}/10")
            st.success(f"💬 {feedback.get('feedback', '')}")

            if q.get("model_answer"):
                with st.expander("📖 모범 답안 보기"):
                    st.markdown(q["model_answer"])
            if q.get("tip"):
                with st.expander("💡 팁 보기"):
                    st.markdown(q["tip"])

            if st.button("다음 질문 →"):
                st.session_state.text_current_idx += 1
                del st.session_state.text_feedback
                st.rerun()

    elif st.session_state.text_state == "report":
        st.markdown("### 🎉 면접 완료")
        with st.spinner("리포트 생성 중..."):
            report = api_get(f"sessions/{st.session_state.text_session_id}/report")
            stats = api_get(f"sessions/{st.session_state.text_session_id}/category-stats")

        if "error" not in report:
            avg = report.get("overall_avg")
            st.metric("전체 평균 점수", f"{avg}/10" if avg else "-")
            st.caption(f"{report.get('answered_questions', 0)}개 질문 답변 완료 / 전체 {report.get('total_questions', 0)}개")

            if "error" not in stats:
                cats = stats.get("categories", [])
                if any(c.get("avg_score") for c in cats):
                    import pandas as pd
                    df = pd.DataFrame([
                        {"카테고리": c["category"], "평균 점수": c["avg_score"] or 0}
                        for c in cats
                    ])
                    st.bar_chart(df.set_index("카테고리"))

            col1, col2 = st.columns(2)
            with col1:
                if report.get("best_answer"):
                    st.success(f"✅ **가장 잘한 답변**\n\n{report['best_answer']['question']}\n\n총점 {report['best_answer']['score']}/10")
            with col2:
                if report.get("worst_answer"):
                    st.error(f"⚠️ **가장 부족한 답변**\n\n{report['worst_answer']['question']}\n\n총점 {report['worst_answer']['score']}/10")

        if st.button("다시 시작"):
            for key in ["text_state", "text_session_id", "text_questions",
                        "text_current_idx", "text_from_cover", "text_feedback"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()


# ──────────────────────────────────────────────
# 페이지: 연습 기록
# ──────────────────────────────────────────────

def show_history():
    """저장된 면접 세션 목록 및 상세 조회"""
    st.title("📋 연습 기록")

    sessions = api_get("sessions?limit=20")
    if isinstance(sessions, dict) and "error" in sessions:
        st.error("기록을 불러올 수 없습니다.")
        return
    if not sessions:
        st.info("저장된 면접 기록이 없습니다.")
        return

    for s in sessions:
        session_id = s.get("id")
        company = s.get("company") or "회사 미상"
        position = s.get("position") or "직무 미상"
        created = s.get("created_at", "")[:10]
        q_count = s.get("question_count", 0)
        a_count = s.get("answer_count", 0)

        with st.expander(f"#{session_id} | {company} — {position} | {created} | 질문 {q_count}개 / 답변 {a_count}회"):
            try:
                detail = api_get(f"sessions/{session_id}/history")
                for q in detail.get("questions", []):
                    st.markdown(f"**🤵 질문:** {q.get('question_text', '')}")
                    for a in q.get("answers", []):
                        st.markdown(f"**🙋 답변:** {a.get('answer_text', '')}")
                        ev = a.get("evaluation")
                        if ev:
                            cols = st.columns(3)
                            cols[0].metric("논리", ev.get("logic_score", "-"))
                            cols[1].metric("구체성", ev.get("specificity_score", "-"))
                            cols[2].metric("총점", f"{ev.get('total_score', '-')}/10")
                            if ev.get("feedback"):
                                st.caption(f"💬 {ev['feedback']}")
                    st.divider()
            except Exception as e:
                st.error(f"상세 기록 로드 실패: {e}")


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────

def main():
    """앱 진입점"""
    st.set_page_config(page_title="AI Career Assistant", page_icon="🤖", layout="wide")
    page = render_sidebar()

    if page == "🏠 홈":
        show_home()
    elif page == "📝 자소서 작성":
        show_cover_letter()
    elif page == "🎤 면접 연습":
        show_text_interview()
    elif page == "📋 연습 기록":
        show_history()


if __name__ == "__main__":
    main()