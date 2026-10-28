import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

def create_architecture_diagram(output_path="architecture_diagram.png"):
    # Configure font
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Segoe UI', 'DejaVu Sans', 'Arial', 'Helvetica']

    fig, ax = plt.subplots(figsize=(22, 14.5), dpi=180)
    bg_canvas = "#F8FAFC"
    ax.set_facecolor(bg_canvas)
    fig.patch.set_facecolor(bg_canvas)
    ax.set_xlim(0, 22)
    ax.set_ylim(0, 14.5)
    ax.axis("off")

    def draw_box(x, y, w, h, bg_color, border_color, tag, title, details=None, radius=0.18, title_color="#0F172A", tag_bg="#E2E8F0", tag_fg="#334155"):
        # Shadow / glow effect
        shadow = FancyBboxPatch((x+0.04, y-0.04), w, h, boxstyle=f"round,pad=0.06,rounding_size={radius}",
                                facecolor="#CBD5E1", edgecolor="none", alpha=0.35, zorder=2)
        ax.add_patch(shadow)

        # Main box
        p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.06,rounding_size={radius}",
                           facecolor=bg_color, edgecolor=border_color, linewidth=1.4, zorder=3)
        ax.add_patch(p)

        # Header tag pill if provided
        ty = y + h - 0.28
        if tag:
            tbox = FancyBboxPatch((x + 0.2, ty - 0.12), len(tag)*0.11 + 0.25, 0.25, boxstyle="round,pad=0.03,rounding_size=0.06",
                                 facecolor=tag_bg, edgecolor="none", zorder=4)
            ax.add_patch(tbox)
            ax.text(x + 0.32, ty, tag, fontsize=7.5, fontweight="bold", color=tag_fg, ha="left", va="center", zorder=5)
            ty -= 0.32

        # Title
        ax.text(x + 0.22, ty, title, fontsize=9.5, fontweight="bold", color=title_color, ha="left", va="center", zorder=5)

        # Details list
        if details:
            ty -= 0.28
            for line in details:
                ax.text(x + 0.22, ty, line, fontsize=7.8, color="#334155", ha="left", va="center", zorder=5)
                ty -= 0.24

    def draw_container(x, y, w, h, bg_color, border_color, label, badge=None, label_color="#0F172A"):
        p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.25",
                           facecolor=bg_color, edgecolor=border_color, linewidth=1.3, linestyle="--", zorder=1)
        ax.add_patch(p)
        ax.text(x + 0.35, y + h - 0.26, label, fontsize=10.5, fontweight="bold", color=label_color, ha="left", va="center", zorder=3)
        if badge:
            bx = x + w - 0.35
            ax.text(bx, y + h - 0.26, badge, fontsize=8.0, fontweight="bold", color="#334155",
                    ha="right", va="center", zorder=3,
                    bbox=dict(boxstyle="round,pad=0.22", facecolor="#E2E8F0", edgecolor="#CBD5E1", linewidth=0.8))

    # =========================================================================
    # HEADER BANNER
    # =========================================================================
    header = FancyBboxPatch((0.6, 13.1), 20.8, 1.05, boxstyle="round,pad=0.08,rounding_size=0.25",
                            facecolor="#064E3B", edgecolor="#047857", linewidth=2.0, zorder=3)
    ax.add_patch(header)
    ax.text(11.0, 13.75, "AgriMind Agentic Platform — System Architecture", 
            fontsize=17, fontweight="bold", color="#FFFFFF", ha="center", va="center", zorder=4)
    ax.text(11.0, 13.38, "Autonomous Farm AI Assistant — Modular Monolith Architecture (FastAPI + LangChain + Gemini 2.5 Flash)",
            fontsize=10.5, color="#A7F3D0", ha="center", va="center", zorder=4)

    # =========================================================================
    # 1. CLIENT / PRESENTATION LAYER
    # =========================================================================
    draw_container(0.6, 11.0, 20.8, 1.85, "#F0FDF4", "#86EFAC", "TIER 1: CLIENT & PRESENTATION LAYER", "React 18 + Vite Web App", "#166534")

    draw_box(0.9, 11.18, 4.8, 1.25, "#FFFFFF", "#10B981", "CHAT UI", "Farmer AgriChat Interface",
             details=["• Conversational diagnostic stream", "• Leaf photo upload & drag-and-drop", "• Structured diagnosis & remedy cards"],
             tag_bg="#D1FAE5", tag_fg="#065F46", title_color="#065F46")

    draw_box(6.0, 11.18, 4.8, 1.25, "#FFFFFF", "#10B981", "FARM MGMT", "Cadastral Farm & Crop Portal",
             details=["• Multi-field registration & soil typing", "• Active crop tracking & planting date", "• Phenological growth stage monitoring"],
             tag_bg="#D1FAE5", tag_fg="#065F46", title_color="#065F46")

    draw_box(11.1, 11.18, 4.8, 1.25, "#FFFFFF", "#10B981", "WEATHER", "Hyperlocal Agro-Weather",
             details=["• Microclimate temp, humidity, wind", "• Delta T chemical spray window index", "• Automatic heat & rainfall alerts"],
             tag_bg="#D1FAE5", tag_fg="#065F46", title_color="#065F46")

    draw_box(16.2, 11.18, 4.9, 1.25, "#FFFFFF", "#10B981", "MARKET", "APMC Mandi Price Ticker",
             details=["• Real-time modal, min & max rates", "• 7-day price band & trend indicators", "• Harvest timing & selling advisories"],
             tag_bg="#D1FAE5", tag_fg="#065F46", title_color="#065F46")

    # Arrow 1: Client -> API Gateway
    arrow1 = FancyArrowPatch((11.0, 11.0), (11.0, 10.45), arrowstyle="->", mutation_scale=18, linewidth=2.2, color="#059669", zorder=6)
    ax.add_patch(arrow1)
    ax.text(11.18, 10.72, "HTTP / REST API & Multipart Form Data (JWT Bearer Token)", fontsize=8.5, fontweight="bold", color="#065F46", va="center", zorder=6)

    # =========================================================================
    # 2. API GATEWAY & SECURITY LAYER
    # =========================================================================
    draw_container(0.6, 8.85, 20.8, 1.55, "#F0FDFA", "#99F6E4", "TIER 2: API ROUTING & SECURITY LAYER", "FastAPI Modular Monolith (:8000)", "#115E59")

    draw_box(0.9, 9.02, 3.8, 0.98, "#FFFFFF", "#14B8A6", "MODULE: AUTH", "Identity & Auth Router",
             details=["• /api/v1/auth/signup & login", "• JWT access token issuance", "• Passlib / Bcrypt password hashing"],
             tag_bg="#CCFBF1", tag_fg="#115E59", title_color="#0F766E")

    draw_box(5.0, 9.02, 4.0, 0.98, "#FFFFFF", "#14B8A6", "MODULE: FARM", "Farm & Crop CRUD Router",
             details=["• /api/v1/farms & /api/v1/crops", "• Soil type & area acreage CRUD", "• User ownership authorization"],
             tag_bg="#CCFBF1", tag_fg="#115E59", title_color="#0F766E")

    draw_box(9.3, 9.02, 4.0, 0.98, "#FFFFFF", "#14B8A6", "MODULE: AGENT", "Agent Gateway Router",
             details=["• /api/v1/agent/chat (multipart)", "• Leaf image byte extraction", "• Farm/crop context retrieval"],
             tag_bg="#CCFBF1", tag_fg="#115E59", title_color="#0F766E")

    draw_box(13.6, 9.02, 3.8, 0.98, "#FFFFFF", "#14B8A6", "MODULE: ALERTS", "Notification Router",
             details=["• /api/v1/notifications query", "• Patch read / unread status", "• Console & email stub dispatch"],
             tag_bg="#CCFBF1", tag_fg="#115E59", title_color="#0F766E")

    draw_box(17.7, 9.02, 3.4, 0.98, "#FFFFFF", "#14B8A6", "TELEMETRY", "Health & Probes",
             details=["• /api/v1/health status", "• /api/v1/health/gemini probe", "• Active mock/live mode flag"],
             tag_bg="#CCFBF1", tag_fg="#115E59", title_color="#0F766E")

    # Arrow 2: API -> Guardrails
    arrow2 = FancyArrowPatch((11.0, 8.85), (11.0, 8.3), arrowstyle="->", mutation_scale=18, linewidth=2.2, color="#0D9488", zorder=6)
    ax.add_patch(arrow2)

    # =========================================================================
    # 3. GUARDRAILS & INPUT SAFETY LAYER
    # =========================================================================
    draw_container(0.6, 6.95, 20.8, 1.3, "#FFFBEB", "#FDE68A", "TIER 3: AI INPUT SAFETY & AGRONOMIC DOMAIN GUARDRAILS", "AgriMindGuardrail", "#92400E")

    draw_box(0.9, 7.1, 6.2, 0.82, "#FFFFFF", "#F59E0B", "GUARDRAIL 1", "Prompt Injection & Safety Filter",
             details=["• Detects prompt injections, jailbreaks, system extraction attempts", "• Immediate deterministic safety refusal return (bypasses LLM)"],
             tag_bg="#FEF3C7", tag_fg="#92400E", title_color="#B45309")

    draw_box(7.4, 7.1, 6.8, 0.82, "#FFFFFF", "#F59E0B", "GUARDRAIL 2", "Agricultural Domain Scope Filter",
             details=["• Identifies off-topic inquiries (programming, finance, general trivia)", "• Returns polite domain boundary guidance to keep focus on farming"],
             tag_bg="#FEF3C7", tag_fg="#92400E", title_color="#B45309")

    draw_box(14.5, 7.1, 6.6, 0.82, "#FFFFFF", "#F59E0B", "IMAGE GATEWAY", "Image Verification & Direct Bypass",
             details=["• Validates MIME format (JPEG/PNG/WEBP) & max 5MB size via Pillow", "• Leaf images bypass text domain filter directly to Vision Diagnostic"],
             tag_bg="#FEF3C7", tag_fg="#92400E", title_color="#B45309")

    # Arrow 3: Guardrails -> Agent Core
    arrow3 = FancyArrowPatch((11.0, 6.95), (11.0, 6.4), arrowstyle="->", mutation_scale=18, linewidth=2.2, color="#D97706", zorder=6)
    ax.add_patch(arrow3)

    # =========================================================================
    # 4. CENTRAL AGENTIC ORCHESTRATION ENGINE
    # =========================================================================
    draw_container(0.6, 4.75, 20.8, 1.6, "#EEF2FF", "#C7D2FE", "TIER 4: CENTRAL AGENTIC ORCHESTRATION ENGINE", "LangChain + Google Gemini 2.5 Flash", "#3730A3")

    draw_box(0.9, 4.92, 4.8, 1.05, "#FFFFFF", "#6366F1", "CORE LOGIC", "Multi-Intent Classifier",
             details=["• 6-intent regex & semantic classifier", "• Prioritized routing: Vision > Rules > RAG", "• Ambiguous query detection & guidance"],
             tag_bg="#E0E7FF", tag_fg="#3730A3", title_color="#4338CA")

    draw_box(6.0, 4.92, 4.8, 1.05, "#FFFFFF", "#6366F1", "CONTEXT INJECTOR", "Agronomic Context Injector",
             details=["• Injects crop species (Tomato, Rice, Wheat)", "• Injects soil composition (Clay, Sandy, Loam)", "• Farm GPS location & seasonal baseline"],
             tag_bg="#E0E7FF", tag_fg="#3730A3", title_color="#4338CA")

    draw_box(11.1, 4.92, 4.8, 1.05, "#FFFFFF", "#6366F1", "DISPATCHER", "Dynamic Tool Calling Harness",
             details=["• Invokes specialized domain tool services", "• Validates typed inputs & outputs via Pydantic", "• Graceful fallback handling on external outage"],
             tag_bg="#E0E7FF", tag_fg="#3730A3", title_color="#4338CA")

    draw_box(16.2, 4.92, 4.9, 1.05, "#FFFFFF", "#6366F1", "SYNTHESIS", "Response Formatter & Advisor",
             details=["• Rich Markdown card formulation", "• Organic vs chemical treatment splits", "• Legal disclaimers & agronomic sign-offs"],
             tag_bg="#E0E7FF", tag_fg="#3730A3", title_color="#4338CA")

    # Arrow 4: Agent Core -> Specialized Tools
    arrow4 = FancyArrowPatch((11.0, 4.75), (11.0, 4.2), arrowstyle="->", mutation_scale=18, linewidth=2.2, color="#4F46E5", zorder=6)
    ax.add_patch(arrow4)

    # =========================================================================
    # 5. SPECIALIZED DOMAIN TOOL SUITE (6 ENGINES)
    # =========================================================================
    draw_container(0.6, 2.35, 20.8, 1.8, "#FAF5FF", "#E9D5FF", "TIER 5: SPECIALIZED DOMAIN ENGINES & TOOL SUITE", "Modular Tools (`app/modules/agent/tools/`)", "#6B21A8")

    draw_box(0.9, 2.5, 3.2, 1.35, "#FFFFFF", "#A855F7", "TOOL 1", "Gemini Vision Disease",
             details=["• Model: Gemini 2.5 Flash", "• Pathology diagnosis", "• Confidence level metric", "• Organic/chemical cure", "• Mock fallback support"],
             tag_bg="#F3E8FF", tag_fg="#6B21A8", title_color="#7E22CE")

    draw_box(4.35, 2.5, 3.2, 1.35, "#FFFFFF", "#A855F7", "TOOL 2", "Irrigation Engine",
             details=["• FAO-56 Penman ET calc", "• Soil moisture capacity", "• Crop coefficient (Kc)", "• Liters / acre schedule", "• Drip & flood advice"],
             tag_bg="#F3E8FF", tag_fg="#6B21A8", title_color="#7E22CE")

    draw_box(7.8, 2.5, 3.2, 1.35, "#FFFFFF", "#A855F7", "TOOL 3", "Fertilizer Engine",
             details=["• N-P-K nutrient balancing", "• Growth stage formulation", "• Basal / top dressing", "• Organic alternative", "• Soil deficiency logic"],
             tag_bg="#F3E8FF", tag_fg="#6B21A8", title_color="#7E22CE")

    draw_box(11.25, 2.5, 3.2, 1.35, "#FFFFFF", "#A855F7", "TOOL 4", "Weather Service",
             details=["• OpenWeatherMap API", "• Hyperlocal temp/rain", "• Thermal stress index", "• Spray window advice", "• Live / mock switch"],
             tag_bg="#F3E8FF", tag_fg="#6B21A8", title_color="#7E22CE")

    draw_box(14.7, 2.5, 3.2, 1.35, "#FFFFFF", "#A855F7", "TOOL 5", "Mandi Intelligence",
             details=["• APMC Mandi dataset", "• Modal, min, max price", "• 7-day rate trends", "• Arbitrage advisory", "• Demo mode data flag"],
             tag_bg="#F3E8FF", tag_fg="#6B21A8", title_color="#7E22CE")

    draw_box(18.15, 2.5, 3.0, 1.35, "#FFFFFF", "#A855F7", "TOOL 6", "Knowledge RAG",
             details=["• Agronomy handbooks", "• Rice/Wheat/Tomato", "• Text chunking (500c)", "• Cosine vector match", "• Semantic retrieval"],
             tag_bg="#F3E8FF", tag_fg="#6B21A8", title_color="#7E22CE")

    # =========================================================================
    # 6. DATA STORAGE & BACKGROUND AUTOMATION (BOTTOM ROW)
    # =========================================================================
    # 6A: Data Platform
    draw_container(0.6, 0.25, 12.0, 1.75, "#EFF6FF", "#BFDBFE", "TIER 6: DATA PLATFORM & VECTOR STORE", "SQLAlchemy ORM + ChromaDB", "#1E40AF")

    draw_box(0.9, 0.45, 5.7, 1.25, "#FFFFFF", "#3B82F6", "SQL DB", "Relational Database (SQLite / Postgres)",
             details=["• Users & Credentials (hashed via Bcrypt)", "• Cadastral Farms & Soil Profiles", "• Active Crop Records & Variety Types", "• Persistent Disease Reports & Notification Logs"],
             tag_bg="#DBEAFE", tag_fg="#1E40AF", title_color="#1D4ED8")

    draw_box(6.85, 0.45, 5.5, 1.25, "#FFFFFF", "#3B82F6", "VECTOR DB", "Agronomic Knowledge Vector Store",
             details=["• Ingested ICAR & Agronomy university guides", "• Tomato Cultivation & Pest Handbook", "• Rice & Wheat Production Agronomy Guide", "• Semantic chunking & embeddings index"],
             tag_bg="#DBEAFE", tag_fg="#1E40AF", title_color="#1D4ED8")

    # 6B: Background Automation Layer
    draw_container(13.0, 0.25, 8.4, 1.75, "#FFF1F2", "#FECDD3", "TIER 7: IN-PROCESS BACKGROUND AUTOMATION", "APScheduler Daemon", "#9F1239")

    draw_box(13.3, 0.45, 7.8, 1.25, "#FFFFFF", "#F43F5E", "SCHEDULER", "APScheduler In-Process Daemon Engine",
             details=["• job_check_weather_alerts (30m): Scans farms for heat/rain threats",
                      "• job_irrigation_reminders (60m): Evaluates soil moisture requirements",
                      "• job_mandi_price_ticker (12h): Fetches APMC market rates twice daily",
                      "• Delivery Stubs: Console logging ('🔔') & Email simulation ('📧')"],
             tag_bg="#FFE4E6", tag_fg="#9F1239", title_color="#BE123C")

    # Arrows from Tools down to Storage
    arrow5 = FancyArrowPatch((6.0, 2.35), (6.0, 2.05), arrowstyle="->", mutation_scale=15, linewidth=1.8, color="#2563EB", zorder=6)
    ax.add_patch(arrow5)

    arrow6 = FancyArrowPatch((17.0, 2.35), (17.0, 2.05), arrowstyle="<->", mutation_scale=15, linewidth=1.8, color="#E11D48", zorder=6)
    ax.add_patch(arrow6)

    plt.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    plt.savefig(output_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"Architecture diagram successfully generated at: {output_path}")

if __name__ == "__main__":
    create_architecture_diagram("architecture_diagram.png")
    create_architecture_diagram("production_artifacts/architecture_diagram.png")
    # Also write into artifacts directory for UI preview
    artifact_dir = r"C:\Users\Karth\.gemini\antigravity\brain\defcb54f-4fb5-4e05-8946-58713d157bda"
    if os.path.exists(artifact_dir):
        create_architecture_diagram(os.path.join(artifact_dir, "architecture_diagram.png"))
