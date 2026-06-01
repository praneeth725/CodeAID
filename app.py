"""
app.py
------
CodeAid: AI-Powered Static Code Analysis and Project Understanding System
Main Streamlit application entry point.

Run with:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import io
import os

# ─────────────────────────────────────────────
# Page configuration (must be first Streamlit call)
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="CodeAid",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Custom CSS — clean, professional, readable
# ─────────────────────────────────────────────

st.markdown("""
<style>
    /* ── Typography & base ── */
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }

    /* ── App background ── */
    .stApp {
        background-color: #0f1117;
        color: #e2e8f0;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background-color: #161b27;
        border-right: 1px solid #2d3748;
    }
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #90cdf4;
    }

    /* ── Main header ── */
    .codeaid-header {
        background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%);
        border: 1px solid #4a5568;
        border-radius: 12px;
        padding: 28px 36px;
        margin-bottom: 24px;
    }
    .codeaid-header h1 {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 2.2rem;
        font-weight: 500;
        color: #90cdf4;
        margin: 0 0 6px 0;
        letter-spacing: -0.5px;
    }
    .codeaid-header p {
        color: #718096;
        font-size: 0.95rem;
        margin: 0;
    }

    /* ── Metric cards ── */
    .metric-card {
        background-color: #1a202c;
        border: 1px solid #2d3748;
        border-radius: 10px;
        padding: 18px 20px;
        text-align: center;
    }
    .metric-card .metric-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 2rem;
        font-weight: 500;
        color: #90cdf4;
        line-height: 1;
        margin-bottom: 4px;
    }
    .metric-card .metric-label {
        font-size: 0.78rem;
        color: #718096;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    /* ── Issue badges ── */
    .badge-error   { background:#742a2a; color:#fed7d7; padding:2px 8px; border-radius:4px; font-size:0.78rem; font-weight:500; }
    .badge-warning { background:#744210; color:#fefcbf; padding:2px 8px; border-radius:4px; font-size:0.78rem; font-weight:500; }
    .badge-info    { background:#1a365d; color:#bee3f8; padding:2px 8px; border-radius:4px; font-size:0.78rem; font-weight:500; }

    /* ── Code blocks ── */
    .stCodeBlock, code {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.85rem !important;
    }

    /* ── Tab styling ── */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1a202c;
        border-radius: 8px 8px 0 0;
        border-bottom: 1px solid #2d3748;
        gap: 0;
    }
    .stTabs [data-baseweb="tab"] {
        color: #718096;
        font-size: 0.88rem;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        color: #90cdf4 !important;
        border-bottom: 2px solid #90cdf4 !important;
        background-color: transparent !important;
    }

    /* ── Expanders ── */
    .streamlit-expanderHeader {
        background-color: #1a202c !important;
        border: 1px solid #2d3748 !important;
        border-radius: 8px !important;
        color: #e2e8f0 !important;
    }

    /* ── Section headers ── */
    .section-title {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #4a90d9;
        border-bottom: 1px solid #2d3748;
        padding-bottom: 8px;
        margin-bottom: 16px;
    }

    /* ── Info boxes ── */
    .info-box {
        background-color: #1a2744;
        border-left: 3px solid #4a90d9;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 0.9rem;
    }
    .success-box {
        background-color: #1a3a2a;
        border-left: 3px solid #48bb78;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 0.9rem;
    }
    .warning-box {
        background-color: #3a2d0a;
        border-left: 3px solid #ecc94b;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 0.9rem;
    }
    .error-box {
        background-color: #3a1010;
        border-left: 3px solid #fc8181;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 0.9rem;
    }

    /* ── Button ── */
    .stButton>button {
        background-color: #2b6cb0;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-family: 'IBM Plex Sans', sans-serif;
        font-weight: 500;
        font-size: 0.95rem;
        transition: background-color 0.2s;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #2c5282;
    }

    /* ── Divider ── */
    hr { border-color: #2d3748; }

    /* ── File tree item ── */
    .file-item {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.82rem;
        color: #a0aec0;
        padding: 3px 0;
    }
    .file-item-issues {
        color: #fc8181;
    }
    .file-item-clean {
        color: #68d391;
    }

    /* ── Suggestion cards ── */
    .suggestion-card {
        background-color: #1a202c;
        border: 1px solid #2d3748;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 10px;
        font-size: 0.9rem;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Imports (after page config)
# ─────────────────────────────────────────────

from core.repo_loader import load_from_github, load_from_zip
from agents.coordinator import Coordinator
from utils.metrics import build_metrics_display


# ─────────────────────────────────────────────
# Session state initialisation
# ─────────────────────────────────────────────

def _init_state():
    defaults = {
        "results": None,
        "repo_name": "",
        "files": [],
        "analysis_done": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

_init_state()


# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    st.markdown("---")

    # ── LLM Selection ────────────────────────
    st.markdown("### 🤖 LLM Agent")
    llm_backend = st.selectbox(
        "Select backend",
        options=["none", "openai", "huggingface"],
        format_func=lambda x: {
            "none": "🚫 Disabled (rule-based only)",
            "openai": "🟢 OpenAI GPT-3.5 (API key required)",
            "huggingface": "🟡 HuggingFace CodeT5 (free, downloads ~300MB)",
        }[x],
        help="Choose the AI backend for enhanced explanations.",
    )

    openai_key = ""
    if llm_backend == "openai":
        openai_key = st.text_input(
            "OpenAI API Key",
            type="password",
            placeholder="sk-...",
            help="Your OpenAI API key. Never stored — only used for this session.",
        )

    if llm_backend == "huggingface":
        st.markdown(
            '<div class="warning-box">⬇️ First run will download ~300MB model to your local cache.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Scanner thresholds ───────────────────
    st.markdown("### 🎛️ Scanner Thresholds")
    max_fn_lines = st.slider(
        "Max function length (lines)",
        min_value=20, max_value=150, value=60, step=5,
        help="Functions longer than this are flagged as 'Long Function'.",
    )
    max_params = st.slider(
        "Max parameters per function",
        min_value=3, max_value=15, value=7, step=1,
        help="Functions with more parameters than this are flagged.",
    )

    st.markdown("---")
    st.markdown("### 📊 CodeXGLUE Evaluation")
    run_eval = st.checkbox(
        "Run benchmark evaluation",
        value=False,
        help="Evaluate CodeAid's scanner against CodeXGLUE samples. Takes ~30s.",
    )
    eval_samples = st.slider(
        "Number of samples",
        min_value=20, max_value=200, value=50, step=10,
        disabled=not run_eval,
    )

    st.markdown("---")
    st.caption("CodeAid v1.0 · Built with Streamlit")
    st.caption("No code is ever executed — analysis is static only.")


# ─────────────────────────────────────────────
# Main header
# ─────────────────────────────────────────────

st.markdown("""
<div class="codeaid-header">
    <h1>🔍 CodeAid</h1>
    <p>AI-powered static code analysis · automatic repair · project understanding</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Input section
# ─────────────────────────────────────────────

st.markdown('<div class="section-title">Repository Input</div>', unsafe_allow_html=True)

input_mode = st.radio(
    "Load repository from",
    options=["github", "zip"],
    format_func=lambda x: "🌐 Public GitHub URL" if x == "github" else "📦 Upload ZIP file",
    horizontal=True,
    label_visibility="collapsed",
)

col_input, col_btn = st.columns([4, 1])

with col_input:
    if input_mode == "github":
        repo_url = st.text_input(
            "GitHub URL",
            placeholder="https://github.com/username/repository",
            label_visibility="collapsed",
        )
        uploaded_zip = None
    else:
        uploaded_zip = st.file_uploader(
            "Upload ZIP",
            type=["zip"],
            label_visibility="collapsed",
        )
        repo_url = ""

with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_clicked = st.button("▶ Analyze", use_container_width=True)


# ─────────────────────────────────────────────
# Run analysis
# ─────────────────────────────────────────────

if analyze_clicked:
    # Validate input
    if input_mode == "github" and not repo_url.strip():
        st.error("Please enter a GitHub repository URL.")
        st.stop()
    if input_mode == "zip" and uploaded_zip is None:
        st.error("Please upload a ZIP file.")
        st.stop()

    st.markdown("---")
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(msg: str, pct: float):
        status_text.markdown(f"**{msg}**")
        progress_bar.progress(min(pct, 1.0))

    try:
        # ── Load files ────────────────────────
        update_progress("📥 Loading repository...", 0.05)

        if input_mode == "github":
            files, repo_name = load_from_github(repo_url.strip())
        else:
            files, repo_name = load_from_zip(uploaded_zip.read())

        update_progress(f"📂 Loaded {len(files)} Python files from '{repo_name}'", 0.08)

        # ── Extract non-Python files for context ──
        extra_files = {}
        if input_mode == "zip" and uploaded_zip is not None:
            # Re-read the zip to get non-python files (README, requirements, etc.)
            import zipfile
            uploaded_zip.seek(0)
            with zipfile.ZipFile(io.BytesIO(uploaded_zip.read()), "r") as zf:
                for name in zf.namelist():
                    basename = name.split("/")[-1].lower()
                    if any(basename.startswith(kw) for kw in
                           ["readme", "requirements", "pyproject", "setup"]):
                        try:
                            extra_files[name] = zf.read(name).decode("utf-8", errors="ignore")
                        except Exception:
                            pass

        # ── Run coordinator ───────────────────
        coordinator = Coordinator(
            llm_backend=llm_backend,
            openai_key=openai_key,
            scanner_config={
                "max_function_lines": max_fn_lines,
                "max_parameters": max_params,
            },
            progress_callback=update_progress,
        )

        results = coordinator.run(files, extra_files=extra_files)
        results["repo_name"] = repo_name

        # ── Store in session state ────────────
        st.session_state.results = results
        st.session_state.repo_name = repo_name
        st.session_state.files = files
        st.session_state.analysis_done = True

        progress_bar.progress(1.0)
        status_text.markdown("**✅ Analysis complete!**")
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Analysis failed: {str(e)}")
        st.stop()


# ─────────────────────────────────────────────
# Results display
# ─────────────────────────────────────────────

if st.session_state.analysis_done and st.session_state.results:
    results = st.session_state.results
    repo_name = results.get("repo_name", "Project")
    scan_summary = results.get("scan_summary", {})
    scan_results = results.get("scan_results", [])
    repair_results = results.get("repair_results", [])
    verification_results = results.get("verification_results", [])
    explanations_by_file = results.get("explanations_by_file", {})
    project_report = results.get("project_report")
    files = results.get("files", [])

    st.markdown("---")

    # ── Pipeline errors (if any) ──────────────
    if results.get("pipeline_errors"):
        with st.expander("⚠️ Pipeline warnings", expanded=False):
            for err in results["pipeline_errors"]:
                st.markdown(f'<div class="warning-box">{err}</div>', unsafe_allow_html=True)

    # ── LLM status ───────────────────────────
    llm_status = results.get("llm_status", "")
    llm_available = results.get("llm_available", False)
    if llm_backend != "none":
        icon = "✅" if llm_available else "❌"
        st.caption(f"{icon} LLM: {llm_status}")

    # ── Summary metric cards ──────────────────
    st.markdown(f'<div class="section-title">Analysis Summary · {repo_name}</div>', unsafe_allow_html=True)

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    metrics_data = [
        (m1, scan_summary.get("total_files", 0), "Files Analyzed"),
        (m2, scan_summary.get("total_lines", 0), "Lines of Code"),
        (m3, scan_summary.get("total_issues", 0), "Issues Found"),
        (m4, scan_summary.get("syntax_errors", 0), "Syntax Errors"),
        (m5, sum(1 for r in repair_results if r.was_modified), "Files Repaired"),
        (m6, scan_summary.get("total_functions", 0), "Functions"),
    ]
    for col, val, label in metrics_data:
        with col:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-value">{val:,}</div>'
                f'<div class="metric-label">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────
    tab_issues, tab_repairs, tab_project, tab_files, tab_metrics, tab_eval = st.tabs([
        "🐛 Issues",
        "🔧 Repairs",
        "🏗️ Project Insights",
        "📁 Files",
        "📊 Metrics",
        "🧪 Evaluation",
    ])

    # ════════════════════════════════════════
    # TAB 1: Issues
    # ════════════════════════════════════════
    with tab_issues:
        all_issues = []
        for sr in scan_results:
            for issue in sr.issues:
                all_issues.append({
                    "File": issue.file,
                    "Line": issue.line or "-",
                    "Type": issue.issue_type,
                    "Severity": issue.severity,
                    "Message": issue.message,
                })

        if not all_issues:
            st.markdown(
                '<div class="success-box">✅ No issues detected! This codebase looks clean.</div>',
                unsafe_allow_html=True,
            )
        else:
            # Issue type breakdown chart
            by_type = scan_summary.get("by_type", {})
            if by_type:
                type_colors = {
                    "SyntaxError": "#fc8181",
                    "UnusedImport": "#f6ad55",
                    "LongFunction": "#f6e05e",
                    "ManyParameters": "#68d391",
                    "TodoComment": "#76e4f7",
                }
                fig = go.Figure(go.Bar(
                    x=list(by_type.keys()),
                    y=list(by_type.values()),
                    marker_color=[type_colors.get(k, "#90cdf4") for k in by_type.keys()],
                    text=list(by_type.values()),
                    textposition="outside",
                ))
                fig.update_layout(
                    paper_bgcolor="#0f1117",
                    plot_bgcolor="#1a202c",
                    font_color="#e2e8f0",
                    font_family="IBM Plex Sans",
                    margin=dict(l=0, r=0, t=10, b=0),
                    height=220,
                    showlegend=False,
                    xaxis=dict(gridcolor="#2d3748"),
                    yaxis=dict(gridcolor="#2d3748", title="Count"),
                )
                st.plotly_chart(fig, use_container_width=True)

            # Issues table
            df = pd.DataFrame(all_issues)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Severity": st.column_config.TextColumn(width="small"),
                    "Line": st.column_config.NumberColumn(width="small"),
                    "Type": st.column_config.TextColumn(width="medium"),
                },
            )

            # Detailed explanations per file
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="section-title">Detailed Explanations</div>', unsafe_allow_html=True)

            for filepath, exps in explanations_by_file.items():
                with st.expander(f"📄 {filepath}  ({len(exps)} issue{'s' if len(exps) != 1 else ''})", expanded=False):
                    for exp in exps:
                        st.markdown(exp.full_text)
                        st.markdown("---")


    # ════════════════════════════════════════
    # TAB 2: Repairs
    # ════════════════════════════════════════
    with tab_repairs:
        modified = [r for r in repair_results if r.was_modified]
        unmodified = [r for r in repair_results if not r.was_modified and r.repairs_skipped]

        if not modified and not unmodified:
            st.markdown(
                '<div class="info-box">ℹ️ No repairs were applicable to this codebase.</div>',
                unsafe_allow_html=True,
            )
        else:
            if modified:
                st.markdown(f"**{len(modified)} file(s) automatically repaired:**")
                for repair in modified:
                    with st.expander(f"✅ {repair.file}  ({len(repair.repairs_applied)} fix(es))", expanded=False):
                        for fix in repair.repairs_applied:
                            st.markdown(f'<div class="success-box">🔧 {fix}</div>', unsafe_allow_html=True)

                        st.markdown("**Repaired code:**")
                        st.code(repair.repaired_source, language="python")

            if unmodified:
                st.markdown(f"<br>**{len(unmodified)} file(s) with issues that need manual attention:**", unsafe_allow_html=True)
                for repair in unmodified:
                    with st.expander(f"⚠️ {repair.file}", expanded=False):
                        for skip in repair.repairs_skipped:
                            st.markdown(f'<div class="warning-box">⚠️ {skip}</div>', unsafe_allow_html=True)

        # Verification results
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">Verification Results</div>', unsafe_allow_html=True)

        v_data = []
        for vr in verification_results:
            if "skipped" not in vr.error_message.lower():
                v_data.append({
                    "File": vr.file,
                    "Status": "✅ Passed" if vr.passed else "❌ Failed",
                    "Details": vr.error_message or "Syntax verified OK",
                })

        if v_data:
            st.dataframe(pd.DataFrame(v_data), use_container_width=True, hide_index=True)
        else:
            st.info("No files were repaired — verification not needed.")


    # ════════════════════════════════════════
    # TAB 3: Project Insights
    # ════════════════════════════════════════
    with tab_project:
        if not project_report:
            st.warning("Project analysis was not available.")
        else:
            pr = project_report

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown('<div class="section-title">Project Classification</div>', unsafe_allow_html=True)
                st.markdown(f"**Type:** {pr.project_type}")
                st.markdown(f"**Architecture:** {pr.architecture}")
                st.markdown(f"**Files analyzed:** {pr.file_count}")
                if pr.architecture_patterns:
                    st.markdown(f"**Patterns detected:** {', '.join(pr.architecture_patterns)}")

            with col_b:
                st.markdown('<div class="section-title">Best Practices Checklist</div>', unsafe_allow_html=True)
                checks = [
                    ("Tests directory", pr.has_tests),
                    ("README file", pr.has_readme),
                    ("Docs directory", pr.has_docs),
                    ("CI/CD config", pr.has_ci),
                    ("Dependency file", pr.dependency_file_found),
                ]
                for label, present in checks:
                    icon = "✅" if present else "❌"
                    st.markdown(f"{icon} {label}")

            st.markdown("<br>", unsafe_allow_html=True)

            # Code metrics
            if pr.metrics:
                st.markdown('<div class="section-title">Code Metrics</div>', unsafe_allow_html=True)
                mc1, mc2, mc3, mc4 = st.columns(4)
                metric_pairs = [
                    (mc1, pr.metrics.get("total_functions", 0), "Functions"),
                    (mc2, pr.metrics.get("total_classes", 0), "Classes"),
                    (mc3, f"{pr.metrics.get('avg_function_length', 0)} lines", "Avg Fn Length"),
                    (mc4, f"{pr.metrics.get('docstring_coverage_pct', 0)}%", "Docstring Coverage"),
                ]
                for col, val, label in metric_pairs:
                    with col:
                        st.markdown(
                            f'<div class="metric-card">'
                            f'<div class="metric-value">{val}</div>'
                            f'<div class="metric-label">{label}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

            st.markdown("<br>", unsafe_allow_html=True)

            # Dependencies
            if pr.dependencies:
                st.markdown('<div class="section-title">Dependencies</div>', unsafe_allow_html=True)
                dep_cols = st.columns(4)
                for i, dep in enumerate(pr.dependencies):
                    dep_cols[i % 4].markdown(f"`{dep}`")

            # Suggestions
            if pr.suggestions:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="section-title">Improvement Suggestions</div>', unsafe_allow_html=True)
                for suggestion in pr.suggestions:
                    st.markdown(
                        f'<div class="suggestion-card">{suggestion}</div>',
                        unsafe_allow_html=True,
                    )

            # LLM summary
            if pr.llm_summary:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="section-title">AI-Generated Project Summary</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="info-box">{pr.llm_summary}</div>',
                    unsafe_allow_html=True,
                )

            # Top imports chart
            if pr.top_imports:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="section-title">Most Used Packages</div>', unsafe_allow_html=True)
                fig2 = go.Figure(go.Bar(
                    x=pr.top_imports,
                    y=[1] * len(pr.top_imports),
                    marker_color="#4a90d9",
                    showlegend=False,
                ))
                fig2.update_layout(
                    paper_bgcolor="#0f1117",
                    plot_bgcolor="#1a202c",
                    font_color="#e2e8f0",
                    margin=dict(l=0, r=0, t=10, b=0),
                    height=180,
                    yaxis_visible=False,
                )
                st.plotly_chart(fig2, use_container_width=True)


    # ════════════════════════════════════════
    # TAB 4: Files
    # ════════════════════════════════════════
    with tab_files:
        st.markdown('<div class="section-title">Repository File Browser</div>', unsafe_allow_html=True)

        issues_per_file = {}
        for sr in scan_results:
            issues_per_file[sr.file] = len(sr.issues)

        # File selector
        file_paths = [f["path"] for f in files]
        selected_file = st.selectbox(
            "Select a file to view",
            options=file_paths,
            format_func=lambda p: (
                f"⚠️ {p}  ({issues_per_file.get(p, 0)} issue{'s' if issues_per_file.get(p, 0) != 1 else ''})"
                if issues_per_file.get(p, 0) > 0
                else f"✅ {p}"
            ),
        )

        if selected_file:
            # Find source
            source = next((f["source"] for f in files if f["path"] == selected_file), "")
            repair = next((r for r in repair_results if r.file == selected_file), None)

            file_issues = issues_per_file.get(selected_file, 0)
            lines = len(source.splitlines())
            st.caption(f"{lines} lines · {file_issues} issue(s)")

            if repair and repair.was_modified:
                view_col1, view_col2 = st.columns(2)
                with view_col1:
                    st.markdown("**Original**")
                    st.code(repair.original_source, language="python")
                with view_col2:
                    st.markdown("**After Repair**")
                    st.code(repair.repaired_source, language="python")
            else:
                st.code(source, language="python")

            # Show issues for this file
            file_scan = next((sr for sr in scan_results if sr.file == selected_file), None)
            if file_scan and file_scan.issues:
                st.markdown("**Issues in this file:**")
                for issue in file_scan.issues:
                    severity_map = {"error": "error-box", "warning": "warning-box", "info": "info-box"}
                    box_class = severity_map.get(issue.severity, "info-box")
                    st.markdown(
                        f'<div class="{box_class}">Line {issue.line}: {issue.message}</div>',
                        unsafe_allow_html=True,
                    )


    # ════════════════════════════════════════
    # TAB 5: Metrics
    # ════════════════════════════════════════
    with tab_metrics:
        st.markdown('<div class="section-title">Pipeline Performance Metrics</div>', unsafe_allow_html=True)

        metrics_display = build_metrics_display(scan_results, repair_results, verification_results)
        scan_m = metrics_display.get("scan", {})
        repair_m = metrics_display.get("repairs", {})
        verify_m = metrics_display.get("verification", {})

        col_s, col_r, col_v = st.columns(3)

        with col_s:
            st.markdown("**🔍 Scanner**")
            st.metric("Files scanned", scan_m.get("total_files", 0))
            st.metric("Issues found", scan_m.get("total_issues", 0))
            st.metric("Files with issues", scan_m.get("files_with_issues", 0))

        with col_r:
            st.markdown("**🔧 Repair Agent**")
            st.metric("Repairs applied", repair_m.get("applied", 0))
            st.metric("Files modified", repair_m.get("files_modified", 0))
            st.metric("Skipped (manual)", repair_m.get("skipped", 0))

        with col_v:
            st.markdown("**✅ Verifier**")
            st.metric("Verifications run", verify_m.get("total", 0))
            st.metric("Passed", verify_m.get("passed", 0))
            pass_rate = verify_m.get("pass_rate", 0)
            st.metric("Pass rate", f"{pass_rate * 100:.1f}%")

        # Issue distribution pie
        by_type = scan_m.get("by_type", {})
        if by_type:
            st.markdown("<br>", unsafe_allow_html=True)
            fig3 = px.pie(
                names=list(by_type.keys()),
                values=list(by_type.values()),
                title="Issue Distribution by Type",
                color_discrete_sequence=["#fc8181", "#f6ad55", "#f6e05e", "#68d391", "#76e4f7"],
                hole=0.4,
            )
            fig3.update_layout(
                paper_bgcolor="#0f1117",
                font_color="#e2e8f0",
                font_family="IBM Plex Sans",
                title_font_color="#90cdf4",
                margin=dict(l=0, r=0, t=40, b=0),
                height=320,
            )
            st.plotly_chart(fig3, use_container_width=True)


    # ════════════════════════════════════════
    # TAB 6: Evaluation (CodeXGLUE)
    # ════════════════════════════════════════
    with tab_eval:
        st.markdown('<div class="section-title">CodeXGLUE Benchmark Evaluation</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="info-box">'
            'This tab evaluates CodeAid\'s detection accuracy against the '
            'CodeXGLUE Devign benchmark. Enable "Run benchmark evaluation" in the sidebar '
            'and click the button below to start.'
            '</div>',
            unsafe_allow_html=True,
        )

        if not run_eval:
            st.info("Enable 'Run benchmark evaluation' in the sidebar to use this tab.")
        else:
            if st.button("▶ Run CodeXGLUE Evaluation", key="run_eval_btn"):
                with st.spinner(f"Running evaluation on {eval_samples} samples..."):
                    try:
                        from utils.codexglue_loader import evaluate_on_devign
                        eval_results = evaluate_on_devign(
                            n_samples=eval_samples,
                            scanner_config={
                                "max_function_lines": max_fn_lines,
                                "max_parameters": max_params,
                            },
                        )

                        st.success(f"✅ Evaluation complete. Dataset: {eval_results['dataset_source']}")

                        e1, e2, e3, e4 = st.columns(4)
                        eval_metrics = [
                            (e1, f"{eval_results['precision']:.3f}", "Precision"),
                            (e2, f"{eval_results['recall']:.3f}", "Recall"),
                            (e3, f"{eval_results['f1']:.3f}", "F1 Score"),
                            (e4, f"{eval_results['accuracy']:.3f}", "Accuracy"),
                        ]
                        for col, val, label in eval_metrics:
                            with col:
                                st.markdown(
                                    f'<div class="metric-card">'
                                    f'<div class="metric-value">{val}</div>'
                                    f'<div class="metric-label">{label}</div>'
                                    f'</div>',
                                    unsafe_allow_html=True,
                                )

                        st.markdown("<br>", unsafe_allow_html=True)

                        # Confusion matrix
                        conf_data = {
                            "": ["Predicted Positive", "Predicted Negative"],
                            "Actual Positive": [eval_results["true_positives"], eval_results["false_negatives"]],
                            "Actual Negative": [eval_results["false_positives"], eval_results["true_negatives"]],
                        }
                        st.markdown("**Confusion Matrix:**")
                        st.dataframe(pd.DataFrame(conf_data).set_index(""), use_container_width=False)

                    except Exception as e:
                        st.error(f"Evaluation failed: {str(e)}")


# ─────────────────────────────────────────────
# Empty state
# ─────────────────────────────────────────────

else:
    st.markdown("""
    <div style="text-align:center; padding: 60px 20px; color: #4a5568;">
        <div style="font-size: 3rem; margin-bottom: 16px;">🔍</div>
        <div style="font-family: 'IBM Plex Mono', monospace; font-size: 1rem; color: #718096;">
            Enter a GitHub URL or upload a ZIP to begin analysis
        </div>
    </div>
    """, unsafe_allow_html=True)
