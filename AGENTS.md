---
description: Operating guidelines and context management protocols for AI development agents working on Tool_ASR Inputer.
---

<!-- 
[說明] 本檔案為 AI Agent 在此專案中的最高行為準則與協作規範。
定義了「以 Repository 為唯一真相來源 (State-in-Repo)」、「分階段里程碑推進 (Phase-by-Phase)」、
「Sub-agent 減壓探索機制」以及「里程碑完成時主動提示開新對話」的標準作業流程。
-->

# Agent Operating Guidelines & Context Management

<!-- 
[第一部分] 專案基礎定位與核心原則
-->
## 1. Project Mission & Core Principles
This project is an ultra-minimalist, local-first, cross-platform (macOS / Windows), Traditional Chinese prioritized AI voice typing tool (`Tool_ASR Inputer`).
- **Local First**: All ASR inference is conducted on the local machine using Qwen3-ASR (0.6B / 1.7B).
- **Traditional Chinese First**: All text processing pipelines prioritize Taiwan Traditional Chinese idioms, punctuation, OpenCC fallback, and deterministic Custom Dictionary corrections.
- **Minimalist UX**: Background tray only (no heavy UI), triggered by `F8` to record and paste directly into the current cursor.

<!-- 
[第二部分] 狀態與上下文管理規範 (Context Management Protocol)
-->
## 2. Context Management Protocol

### 2.1 State-in-Repo (Repository as Single Source of Truth)
Do not rely on conversational context to track project state or architecture decisions.
1. **Mandatory Start Step**: At the start of ANY session or task, always inspect:
   - [PROGRESS.md](file:///Users/lazxwe/Documents/GitHub/Tool_ASR%20Inputer/PROGRESS.md)
   - [doc/開發規格.md](file:///Users/lazxwe/Documents/GitHub/Tool_ASR%20Inputer/doc/%E9%96%8B%E7%99%BC%E8%A6%8F%E6%A0%BC.md)
   - [doc/推薦技術清單.md](file:///Users/lazxwe/Documents/GitHub/Tool_ASR%20Inputer/doc/%E6%8E%A8%E8%96%A6%E6%8A%80%E8%A1%93%E6%B8%85%E5%96%AE.md)
   - [doc/Qwen3-ASR技術規格與整合筆記.md](file:///Users/lazxwe/Documents/GitHub/Tool_ASR%20Inputer/doc/Qwen3-ASR%E6%8A%80%E8%A1%93%E8%A6%8F%E6%A0%BC%E8%88%87%E6%95%B4%E5%90%88%E7%AD%86%E8%A8%98.md)
2. **Local Specs First (Zero-Redundant Web Search)**: All model APIs, parameters, audio formats, and integration notes are curated in `doc/Qwen3-ASR技術規格與整合筆記.md`. Do NOT perform redundant web searches for Qwen3-ASR specs; read local documentation directly.
3. **Synchronize Progress**: Whenever a task or phase is completed and verified, update [PROGRESS.md](file:///Users/lazxwe/Documents/GitHub/Tool_ASR%20Inputer/PROGRESS.md) immediately with checkboxes and verification notes.

### 2.2 Sub-agent Delegation for Heavy Tasks
To avoid context pollution in the main conversation thread:
- Use sub-agents when performing extensive log debugging, exploratory package testing, or verbose command inspection.
- The sub-agent should summarize findings cleanly back to the main agent.

### 2.3 Milestone Completion & New Session Handover (CRITICAL)
- When a Phase / Milestone is fully completed and all automated verification tests pass:
  1. Update [PROGRESS.md](file:///Users/lazxwe/Documents/GitHub/Tool_ASR%20Inputer/PROGRESS.md).
  2. Create / update the walkthrough summary.
  3. **MANDATORY**: Proactively prompt the user to start a **new chat session** for the next Phase to maintain optimal reasoning clarity and prevent context drift.

<!-- 
[第三部分] 開發與環境規範
-->
## 3. Environment & Development Conventions
- **Isolated Virtual Environment**: Always execute Python commands and scripts using the local virtual environment (`.venv/bin/python`, `.venv/bin/pytest`, etc.).
- **Model Cache Isolation**: Ensure local ASR models are downloaded/cached inside the project directory (e.g. `./models/`) so deleting the repository cleanly removes all assets.
- **Test-Driven Reliability**: Every text processing, dictionary replacement, and configuration module MUST have unit tests in `tests/` verifying edge cases.
- **Language Requirements**: Internal reasoning in English; user-facing responses in **Traditional Chinese (繁體中文)**.
