#!/usr/bin/env python3
"""
LuoOS Setup — First-Run Configuration Wizard
Runs once on first launch. Creates ~/.luo_os/config.json.
After setup, every future start.py skips straight to boot.
"""
import os
import sys
import json
import time
import shutil
import subprocess
from pathlib import Path

# ── Colours ────────────────────────────────────────────────────────
C  = "\033[96m"   # cyan
G  = "\033[92m"   # green
Y  = "\033[93m"   # yellow
R  = "\033[0m"    # reset
B  = "\033[1m"    # bold
DIM= "\033[2m"    # dim
M  = "\033[95m"   # magenta
W  = "\033[97m"   # white

def cls():
    os.system("cls" if os.name == "nt" else "clear")

def hr(char="─", width=58, color=C):
    print(f"{color}  {''.join([char]*width)}{R}")

def header(title, subtitle=""):
    cls()
    print(f"\n{B}{C}  LuoOS Setup{R}")
    hr()
    print(f"{W}  {title}{R}")
    if subtitle:
        print(f"{DIM}  {subtitle}{R}")
    hr()
    print()

def ask(prompt, default=None, options=None, color=W):
    """Ask a question, return answer."""
    if options:
        for i, (key, label) in enumerate(options, 1):
            marker = f"{G}●{R}" if i == 1 else f"{DIM}○{R}"
            print(f"    {marker} {i}. {label}")
        print()
        default_num = 1
        while True:
            try:
                val = input(f"{color}  › {R}").strip()
                if not val:
                    return options[default_num - 1][0]
                idx = int(val) - 1
                if 0 <= idx < len(options):
                    return options[idx][0]
                print(f"  {Y}Enter a number 1–{len(options)}{R}")
            except (ValueError, KeyboardInterrupt):
                return options[default_num - 1][0]
    else:
        if default:
            prompt = f"{prompt} {DIM}[{default}]{R}"
        try:
            val = input(f"{color}  {prompt}: {R}").strip()
            return val if val else default
        except KeyboardInterrupt:
            return default

def ask_yn(prompt, default=True):
    hint = f"{G}Y{R}/{DIM}n{R}" if default else f"{DIM}y{R}/{G}N{R}"
    try:
        val = input(f"  {prompt} ({hint}): ").strip().lower()
        if not val:
            return default
        return val in ("y", "yes", "1", "true")
    except KeyboardInterrupt:
        return default

def tick(msg):
    print(f"  {G}✅{R}  {msg}")

def info(msg):
    print(f"  {C}→{R}  {msg}")

def warn(msg):
    print(f"  {Y}⚠{R}   {msg}")

def bold(msg):
    print(f"  {B}{W}{msg}{R}")


# ── Config paths ────────────────────────────────────────────────────
LUO_DIR    = Path.home() / ".luo_os"
CONFIG_PATH = LUO_DIR / "config.json"
MODELS_DIR  = LUO_DIR / "models"

LUO_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# ── System detection ────────────────────────────────────────────────
import platform
_plat    = platform.system()
_machine = platform.machine()
_py      = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
_ram_gb  = 4  # default fallback
try:
    import psutil
    _ram_gb = psutil.virtual_memory().total // (1024**3)
except Exception:
    try:
        if _plat == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if "MemTotal" in line:
                        _ram_gb = int(line.split()[1]) // (1024**2)
                        break
    except Exception:
        pass

_cpu_cores = os.cpu_count() or 4
_has_gpu   = False
try:
    result = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                            capture_output=True, text=True, timeout=3)
    if result.returncode == 0 and result.stdout.strip():
        _has_gpu = True
except Exception:
    pass

def _recommend_model():
    """Recommend the best model for this machine."""
    if _ram_gb >= 8:
        return "phi3.5"
    elif _ram_gb >= 4:
        return "qwen2.5-3b"
    else:
        return "qwen2.5-1.5b"



# ── 60 Most-used API keys ─────────────────────────────────────────
API_KEY_CATALOG = [
    # AI & ML
    ("OPENAI_API_KEY",          "OpenAI",              "ai",        "GPT-4, DALL-E, Whisper"),
    ("ANTHROPIC_API_KEY",       "Anthropic",           "ai",        "Claude 3.5 Sonnet, Haiku"),
    ("GOOGLE_AI_API_KEY",       "Google AI (Gemini)",  "ai",        "Gemini Pro, Gemini Flash"),
    ("COHERE_API_KEY",          "Cohere",              "ai",        "Command, Embed, Rerank"),
    ("MISTRAL_API_KEY",         "Mistral AI",          "ai",        "Mistral Large, Codestral"),
    ("GROQ_API_KEY",            "Groq",                "ai",        "Llama3, Mixtral — ultra fast"),
    ("TOGETHER_API_KEY",        "Together AI",         "ai",        "Open source models"),
    ("REPLICATE_API_TOKEN",     "Replicate",           "ai",        "Run any ML model"),
    ("HUGGINGFACE_TOKEN",       "Hugging Face",        "ai",        "Models, datasets, spaces"),
    ("STABILITY_API_KEY",       "Stability AI",        "ai",        "Stable Diffusion"),
    ("ELEVENLABS_API_KEY",      "ElevenLabs",          "ai",        "Voice synthesis"),
    ("DEEPGRAM_API_KEY",        "Deepgram",            "ai",        "Speech-to-text"),
    # Search & Web
    ("SERPAPI_API_KEY",         "SerpAPI",             "search",    "Google Search results"),
    ("BRAVE_API_KEY",           "Brave Search",        "search",    "Privacy-first search"),
    ("BING_SEARCH_KEY",         "Bing Search",         "search",    "Microsoft Bing API"),
    ("GOOGLE_SEARCH_KEY",       "Google Search",       "search",    "Google Custom Search"),
    ("TAVILY_API_KEY",          "Tavily",              "search",    "AI-optimised web search"),
    # Cloud
    ("AWS_ACCESS_KEY_ID",       "AWS",                 "cloud",     "Amazon Web Services"),
    ("GOOGLE_CLOUD_KEY",        "Google Cloud",        "cloud",     "GCP services"),
    ("AZURE_API_KEY",           "Microsoft Azure",     "cloud",     "Azure Cognitive Services"),
    ("CLOUDFLARE_API_TOKEN",    "Cloudflare",          "cloud",     "CDN, Workers, R2"),
    ("VERCEL_TOKEN",            "Vercel",              "cloud",     "Deployments, Edge"),
    ("NETLIFY_TOKEN",           "Netlify",             "cloud",     "Static sites, Functions"),
    ("DIGITALOCEAN_TOKEN",      "DigitalOcean",        "cloud",     "Droplets, K8s, Spaces"),
    # Data & Storage
    ("SUPABASE_KEY",            "Supabase",            "data",      "Postgres + Auth + Storage"),
    ("MONGODB_URI",             "MongoDB Atlas",       "data",      "Cloud database"),
    ("REDIS_URL",               "Redis Cloud",         "data",      "Cache + pub/sub"),
    ("PINECONE_API_KEY",        "Pinecone",            "data",      "Vector database"),
    ("WEAVIATE_API_KEY",        "Weaviate",            "data",      "Vector search"),
    ("PLANETSCALE_TOKEN",       "PlanetScale",         "data",      "Serverless MySQL"),
    # Communication
    ("TWILIO_AUTH_TOKEN",       "Twilio",              "comm",      "SMS, voice, WhatsApp"),
    ("SENDGRID_API_KEY",        "SendGrid",            "comm",      "Transactional email"),
    ("RESEND_API_KEY",          "Resend",              "comm",      "Email for developers"),
    ("MAILGUN_API_KEY",         "Mailgun",             "comm",      "Email API"),
    ("SLACK_BOT_TOKEN",         "Slack",               "comm",      "Slack bot + webhooks"),
    ("DISCORD_BOT_TOKEN",       "Discord",             "comm",      "Discord bot"),
    ("TELEGRAM_BOT_TOKEN",      "Telegram",            "comm",      "Telegram bot"),
    # Payments & Finance
    ("STRIPE_SECRET_KEY",       "Stripe",              "payments",  "Payments, subscriptions"),
    ("PAYPAL_CLIENT_SECRET",    "PayPal",              "payments",  "PayPal checkout"),
    ("COINBASE_API_KEY",        "Coinbase",            "payments",  "Crypto payments"),
    ("PLAID_SECRET",            "Plaid",               "payments",  "Bank data, fintech"),
    # Analytics & Monitoring
    ("MIXPANEL_TOKEN",          "Mixpanel",            "analytics", "Product analytics"),
    ("SEGMENT_WRITE_KEY",       "Segment",             "analytics", "Data pipeline"),
    ("AMPLITUDE_API_KEY",       "Amplitude",           "analytics", "Behavioural analytics"),
    ("DATADOG_API_KEY",         "Datadog",             "analytics", "Monitoring + APM"),
    ("SENTRY_DSN",              "Sentry",              "analytics", "Error tracking"),
    ("POSTHOG_API_KEY",         "PostHog",             "analytics", "Open source analytics"),
    # Developer Tools
    ("GITHUB_TOKEN",            "GitHub",              "dev",       "Repos, Actions, APIs"),
    ("GITLAB_TOKEN",            "GitLab",              "dev",       "GitLab API"),
    ("JIRA_API_TOKEN",          "Jira",                "dev",       "Project management"),
    ("LINEAR_API_KEY",          "Linear",              "dev",       "Issue tracking"),
    ("NOTION_TOKEN",            "Notion",              "dev",       "Workspace API"),
    ("AIRTABLE_API_KEY",        "Airtable",            "dev",       "No-code database"),
    # Maps & Location
    ("GOOGLE_MAPS_KEY",         "Google Maps",         "maps",      "Maps, geocoding, places"),
    ("MAPBOX_TOKEN",            "Mapbox",              "maps",      "Custom maps"),
    ("OPENWEATHER_KEY",         "OpenWeatherMap",      "maps",      "Weather data"),
    # Auth & Security
    ("AUTH0_CLIENT_SECRET",     "Auth0",               "auth",      "Authentication platform"),
    ("CLERK_SECRET_KEY",        "Clerk",               "auth",      "User management"),
    ("FIREBASE_SECRET",         "Firebase",            "auth",      "Google Firebase"),
    # Media & Content
    ("CLOUDINARY_API_SECRET",   "Cloudinary",          "media",     "Image + video CDN"),
    ("YOUTUBE_API_KEY",         "YouTube Data",        "media",     "YouTube API v3"),
]

# ════════════════════════════════════════════════════════════════════
# SETUP WIZARD
# ════════════════════════════════════════════════════════════════════

def run_setup():
    config = {}

    # ── Welcome ─────────────────────────────────────────────────────
    cls()
    print(f"""
{B}{C}
  ██╗     ██╗   ██╗ ██████╗      ██████╗ ███████╗
  ██║     ██║   ██║██╔═══██╗    ██╔═══██╗██╔════╝
  ██║     ██║   ██║██║   ██║    ██║   ██║███████╗
  ██║     ██║   ██║██║   ██║    ██║   ██║╚════██║
  ███████╗╚██████╔╝╚██████╔╝    ╚██████╔╝███████║
  ╚══════╝ ╚═════╝  ╚═════╝      ╚═════╝ ╚══════╝{R}

{W}  Welcome to LuoOS — The AI-Native Operating System{R}
{DIM}  Built by Luo Kai · First-run setup · Takes about 60 seconds{R}
""")
    hr()
    print(f"  {DIM}System detected:{R}")
    print(f"  {G}  OS:{R}    {_plat} {_machine}")
    print(f"  {G}  Python:{R} {_py}")
    print(f"  {G}  RAM:{R}   {_ram_gb}GB")
    print(f"  {G}  CPU:{R}   {_cpu_cores} cores")
    if _has_gpu:
        print(f"  {G}  GPU:{R}   NVIDIA detected ✅")
    hr()
    print()
    input(f"  {C}Press Enter to begin setup...{R} ")

    # ── Step 1: Your name ────────────────────────────────────────────
    header("Step 1 of 5 — Who are you?",
           "LUOKAI personalises responses using your name")
    print(f"  {DIM}This is stored locally, never sent anywhere.{R}\n")
    name = ask("Your name", default="User")
    config["user_name"] = name or "User"
    tick(f"Hello, {config['user_name']}!")

    # ── Step 2: AI Model ─────────────────────────────────────────────
    recommended = _recommend_model()
    header("Step 2 of 5 — Choose your AI model",
           "LUOKAI's brain — runs fully offline on your machine")

    print(f"  {DIM}Your machine has {_ram_gb}GB RAM · {_cpu_cores} CPU cores{R}\n")

    model_options = [
        ("qwen2.5-1.5b", f"Qwen2.5 1.5B  {DIM}~900MB · 2GB RAM · Fast · Good quality{R}"),
        ("qwen2.5-3b",   f"Qwen2.5 3B    {DIM}~1.8GB · 4GB RAM · Better quality{R}  {Y}{'← Recommended' if recommended=='qwen2.5-3b' else ''}{R}"),
        ("phi3.5",       f"Phi-3.5 mini  {DIM}~2.2GB · 4GB RAM · Best quality{R}     {Y}{'← Recommended' if recommended=='phi3.5' else ''}{R}"),
        ("none",         f"No model      {DIM}Cell system only (instant, no download){R}"),
    ]
    # Reorder so recommended is first
    rec_idx = [i for i, (k,_) in enumerate(model_options) if k == recommended]
    if rec_idx:
        model_options.insert(0, model_options.pop(rec_idx[0]))

    print(f"  {C}Which AI model should LUOKAI use?{R}\n")
    model_choice = ask("", options=model_options)
    config["ai_model"] = model_choice

    model_labels = {
        "qwen2.5-1.5b": "Qwen2.5 1.5B (900MB)",
        "qwen2.5-3b":   "Qwen2.5 3B (1.8GB)",
        "phi3.5":       "Phi-3.5 mini (2.2GB)",
        "none":         "Cell system only",
    }
    tick(f"AI model: {model_labels.get(model_choice, model_choice)}")

    if model_choice != "none":
        print()
        dl_now = ask_yn("  Download the model now? (happens in background if No)", default=True)
        config["download_model_now"] = dl_now

    # ── Step 2.5: API Keys ──────────────────────────────────────────
    header("Step 3 of 6 — API Keys (optional)",
           "Connect LUOKAI to external services for extra capabilities")

    print(f"  {DIM}All keys stored locally in ~/.luo_os/config.json — never sent anywhere.{R}")
    print(f"  {DIM}Skip any you don't have. You can add them later by editing config.json{R}")

    config["api_keys"] = {}
    categories = {}
    for env_key, name, cat, desc in API_KEY_CATALOG:
        categories.setdefault(cat, []).append((env_key, name, desc))

    cat_labels = {
        "ai": "🤖 AI & Machine Learning",
        "search": "🔍 Search & Web",
        "cloud": "☁️  Cloud Platforms",
        "data": "🗄️  Databases & Storage",
        "comm": "💬 Communication",
        "payments": "💳 Payments & Finance",
        "analytics": "📊 Analytics & Monitoring",
        "dev": "🛠️  Developer Tools",
        "maps": "🗺️  Maps & Location",
        "auth": "🔐 Auth & Security",
        "media": "🎬 Media & Content",
    }

    add_any = ask_yn("  Add any API keys now?", default=False)
    if add_any:
        for cat_key, entries in categories.items():
            print(f"\n  {W}{cat_labels.get(cat_key, cat_key)}{R}")
            for env_key, name, desc in entries:
                val = ask(f"  {name} {DIM}({desc}){R}", default="")
                if val and val.strip():
                    config["api_keys"][env_key] = val.strip()
                    # Also set in environment immediately
                    import os as _os
                    _os.environ[env_key] = val.strip()

    added = len(config["api_keys"])
    if added:
        tick(f"{added} API key{'s' if added != 1 else ''} saved")
    else:
        info("No API keys added — LUOKAI works great without them")

    # ── Step 3: Appearance ───────────────────────────────────────────
    header("Step 4 of 6 — Appearance",
           "How should LuoOS look?")

    print(f"  {C}Theme:{R}\n")
    theme = ask("", options=[
        ("dark",    f"Dark          {DIM}Dark background, light text (default){R}"),
        ("darker",  f"Darker        {DIM}Pure black, high contrast{R}"),
        ("light",   f"Light         {DIM}White background, dark text{R}"),
        ("hacker",  f"Hacker        {DIM}Black + green terminal aesthetic{R}"),
        ("ocean",   f"Ocean         {DIM}Deep blue tones{R}"),
    ])
    config["theme"] = theme
    tick(f"Theme: {theme}")

    print()
    print(f"  {C}Wallpaper style:{R}\n")
    wallpaper = ask("", options=[
        ("gradient", f"Gradient      {DIM}Smooth colour gradient (default){R}"),
        ("minimal",  f"Minimal       {DIM}Solid colour, no distractions{R}"),
        ("particles",f"Particles     {DIM}Animated floating particles{R}"),
        ("none",     f"None          {DIM}Plain background{R}"),
    ])
    config["wallpaper"] = wallpaper
    tick(f"Wallpaper: {wallpaper}")

    print()
    print(f"  {C}Desktop mode:{R}\n")
    ui_mode = ask("", options=[
        ("3d",      f"3D Spatial    {DIM}Four floating screens, 3D parallax, drag anywhere{R}  {Y}← New{R}"),
        ("classic", f"Classic       {DIM}Traditional desktop layout (default){R}"),
    ])
    config["ui_mode"] = ui_mode
    tick(f"Desktop: {'3D Spatial' if ui_mode == '3d' else 'Classic'}")

    # ── Step 3.5: API Keys ───────────────────────────────────────────
    header("Step 4 of 6 — API Keys (optional)",
           "Connect external services to LuoOS — skip any you don't need")

    config["api_keys"] = {}
    print(f"  {DIM}Keys are stored in ~/.luo_os/config.json (local only, never sent anywhere){R}")
    print(f"  {DIM}Press Enter to skip any key. You can add keys later by editing config.json{R}")

    add_keys = ask_yn("  Would you like to add any API keys now?", default=False)

    if add_keys:
        # Group by category
        categories = [
            ("🤖 AI & LLM",          ["openai","anthropic","google_ai","mistral","cohere","groq","together","replicate","huggingface","perplexity"]),
            ("🔍 Search & Web",       ["serpapi","brave_search","tavily","bing_search","exa"]),
            ("Cloud",              ["aws","gcp","azure","cloudflare","vercel"]),
            ("💻 Dev & Code",          ["github","gitlab","linear","supabase","firebase"]),
            ("💬 Communication",       ["twilio","sendgrid","slack","discord","telegram"]),
            ("💳 Payments",            ["stripe","paypal","plaid"]),
            ("📊 Data & Analytics",    ["pinecone","airtable","notion","mongodb"]),
            ("Maps & Weather",     ["google_maps","mapbox","openweather"]),
            ("🎵 Media & Voice",       ["cloudinary","elevenlabs","deepgram","spotify"]),
            ("🔐 Auth & Monitoring",   ["auth0","datadog","sentry","posthog"]),
            ("📰 Misc",                ["newsapi","alpha_vantage","coinbase"]),
        ]

        provider_map = {p[0]: p for p in API_PROVIDERS}

        for cat_name, keys in categories:
            print(f"\n  {B}{cat_name}{R}")
            any_in_cat = False
            for key in keys:
                if key not in provider_map:
                    continue
                pid, name, desc = provider_map[key]
                val = ask(f"  {name} {DIM}({desc}){R}", default="")
                if val and val.strip():
                    config["api_keys"][key] = val.strip()
                    tick(f"{name} key saved")
                    any_in_cat = True
            if not any_in_cat:
                pass  # silently skip empty categories

        total_keys = len(config["api_keys"])
        if total_keys:
            tick(f"{total_keys} API key{'s' if total_keys > 1 else ''} saved")
        else:
            info("No keys added — you can add them later in ~/.luo_os/config.json")
    else:
        info("Skipped — add API keys later in ~/.luo_os/config.json")

    # ── Step 5: Features ─────────────────────────────────────────────
    header("Step 5 of 6 — Features",
           "Enable or disable LUOKAI capabilities")

    print()
    config["features"] = {}

    features = [
        ("voice",      "Voice interface",        "Talk to LUOKAI — speech-to-text + responses",       True),
        ("coevo",      "Co-evolution engine",     "LUOKAI learns and improves itself over time",        True),
        ("neural",     "Neural interface",        "Cortical Labs CL1 biological neuron bridge (sim)",   True),
        ("autolearn",  "Auto-learn",              "LUOKAI learns from your conversations",              True),
        ("vscode",     "VS Code integration",     "Embedded code editor in LuoOS",                     False),
    ]

    for key, name, desc, default in features:
        print(f"  {W}{name}{R}")
        print(f"  {DIM}  {desc}{R}")
        enabled = ask_yn(f"  Enable {name}?", default=default)
        config["features"][key] = enabled
        status = f"{G}enabled{R}" if enabled else f"{DIM}disabled{R}"
        print(f"  → {status}\n")

    # ── Step 5: Port & auto-open ─────────────────────────────────────
    header("Step 6 of 6 — Startup preferences",
           "How should LuoOS start?")

    print(f"  {C}Server port:{R}\n")
    port_opts = [
        ("3000", f"3000  {DIM}Default{R}"),
        ("8080", f"8080  {DIM}Alternative{R}"),
        ("custom", f"Custom  {DIM}Enter your own{R}"),
    ]
    port_choice = ask("", options=port_opts)
    if port_choice == "custom":
        port_val = ask("Enter port number", default="3000")
        try:
            port_val = str(int(port_val))
        except ValueError:
            port_val = "3000"
        config["port"] = int(port_val)
    else:
        config["port"] = int(port_choice)
    tick(f"Port: {config['port']}")

    print()
    config["auto_open_browser"] = ask_yn("  Auto-open browser on start?", default=True)
    tick(f"Auto-open browser: {'yes' if config['auto_open_browser'] else 'no'}")

    print()
    config["show_startup_tips"] = ask_yn("  Show tips on startup?", default=True)

    # ── Summary ──────────────────────────────────────────────────────
    header("Setup complete — here's your configuration")

    print(f"  {W}User:{R}          {config['user_name']}")
    print(f"  {W}AI Model:{R}      {model_labels.get(config['ai_model'], config['ai_model'])}")
    print(f"  {W}Theme:{R}         {config['theme']}")
    print(f"  {W}Wallpaper:{R}     {config['wallpaper']}")
    print(f"  {W}Port:{R}          {config['port']}")
    print(f"  {W}Auto-browser:{R}  {'yes' if config['auto_open_browser'] else 'no'}")
    print()
    print(f"  {W}Features:{R}")
    for key, name, _, _ in features:
        status = f"{G}✅ on {R}" if config["features"].get(key) else f"{DIM}○ off{R}"
        print(f"    {status}  {name}")
    print()
    hr()
    print()

    confirm = ask_yn("  Save this configuration and launch LuoOS?", default=True)
    if not confirm:
        print(f"\n  {Y}Setup cancelled. Run start.py again to redo setup.{R}\n")
        sys.exit(0)

    # ── Save config ──────────────────────────────────────────────────
    config["setup_complete"]  = True
    config["setup_version"]   = "1.0"
    config["setup_timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    tick(f"Config saved → {CONFIG_PATH}")

    # ── Apply theme to index.html ────────────────────────────────────
    _apply_config(config)

    print(f"\n  {G}{B}LuoOS is configured and ready!{R}")
    print(f"  {DIM}Settings saved to {CONFIG_PATH}{R}")
    print(f"  {DIM}To reconfigure: delete that file and restart{R}\n")
    time.sleep(1)

    return config


# ════════════════════════════════════════════════════════════════════
# CONFIG APPLICATION
# ════════════════════════════════════════════════════════════════════


# ── 60 most-used API providers ──────────────────────────────────────
API_PROVIDERS = [
    # AI & LLM
    ("openai",          "OpenAI",               "GPT-4, DALL-E, Whisper"),
    ("anthropic",       "Anthropic",            "Claude models"),
    ("google_ai",       "Google AI (Gemini)",   "Gemini Pro, Flash"),
    ("mistral",         "Mistral AI",           "Mistral, Mixtral models"),
    ("cohere",          "Cohere",               "Command, Embed models"),
    ("groq",            "Groq",                 "Ultra-fast LLM inference"),
    ("together",        "Together AI",          "Open-source model hosting"),
    ("replicate",       "Replicate",            "Image/video/audio AI"),
    ("huggingface",     "Hugging Face",         "Model hub + Inference API"),
    ("perplexity",      "Perplexity AI",        "AI-powered search"),
    # Search & Web
    ("serpapi",         "SerpAPI",              "Google Search results"),
    ("brave_search",    "Brave Search",         "Privacy-focused search"),
    ("tavily",          "Tavily",               "AI-optimised web search"),
    ("bing_search",     "Bing Search",          "Microsoft web search"),
    ("exa",             "Exa.ai",               "Neural search engine"),
    # Cloud
    ("aws",             "AWS",                  "S3, Lambda, EC2 etc."),
    ("gcp",             "Google Cloud",         "GCS, BigQuery, etc."),
    ("azure",           "Microsoft Azure",      "Azure services"),
    ("cloudflare",      "Cloudflare",           "CDN, Workers, R2"),
    ("vercel",          "Vercel",               "Deployments + Edge"),
    # Dev & Code
    ("github",          "GitHub",               "Repos, Actions, Copilot"),
    ("gitlab",          "GitLab",               "CI/CD, repos"),
    ("linear",          "Linear",               "Issue tracking"),
    ("jira",            "Jira / Atlassian",     "Project management"),
    ("supabase",        "Supabase",             "Postgres + auth + storage"),
    ("firebase",        "Firebase",             "Realtime DB + auth"),
    ("planetscale",     "PlanetScale",          "Serverless MySQL"),
    ("neon",            "Neon",                 "Serverless Postgres"),
    # Communication
    ("twilio",          "Twilio",               "SMS, voice, WhatsApp"),
    ("sendgrid",        "SendGrid",             "Transactional email"),
    ("mailgun",         "Mailgun",              "Email API"),
    ("slack",           "Slack",                "Messaging + bots"),
    ("discord",         "Discord",              "Bot API"),
    ("telegram",        "Telegram",             "Bot API"),
    ("whatsapp",        "WhatsApp Business",    "Messaging API"),
    # Payments & Finance
    ("stripe",          "Stripe",               "Payments + billing"),
    ("paypal",          "PayPal",               "Payments"),
    ("plaid",           "Plaid",                "Banking data"),
    ("coinbase",        "Coinbase",             "Crypto"),
    # Data & Analytics
    ("pinecone",        "Pinecone",             "Vector database"),
    ("weaviate",        "Weaviate",             "Vector + GraphQL DB"),
    ("airtable",        "Airtable",             "Spreadsheet DB"),
    ("notion",          "Notion",               "Docs + DB API"),
    ("mongodb",         "MongoDB Atlas",        "Cloud MongoDB"),
    # Maps & Location
    ("google_maps",     "Google Maps",          "Geocoding, directions"),
    ("mapbox",          "Mapbox",               "Custom maps"),
    ("openweather",     "OpenWeatherMap",       "Weather data"),
    # Media
    ("cloudinary",      "Cloudinary",           "Image/video CDN"),
    ("youtube",         "YouTube Data",         "Videos, channels"),
    ("spotify",         "Spotify",              "Music API"),
    ("elevenlabs",      "ElevenLabs",           "Text-to-speech AI"),
    ("deepgram",        "Deepgram",             "Speech-to-text AI"),
    # Auth & Security
    ("auth0",           "Auth0",                "Authentication"),
    ("okta",            "Okta",                 "Enterprise identity"),
    # Monitoring & Infra
    ("datadog",         "Datadog",              "Monitoring + APM"),
    ("sentry",          "Sentry",               "Error tracking"),
    ("posthog",         "PostHog",              "Product analytics"),
    ("grafana",         "Grafana Cloud",        "Dashboards + alerts"),
    # Misc
    ("newsapi",         "NewsAPI",              "Live news articles"),
    ("alpha_vantage",   "Alpha Vantage",        "Stock market data"),
]

THEMES = {
    "dark": {
        "--bg":        "#0d0d0d",
        "--bg-card":   "#141414",
        "--bg-input":  "#1a1a1a",
        "--border":    "#2a2a2a",
        "--text":      "#e8e8e8",
        "--text2":     "#999999",
        "--text3":     "#555555",
        "--accent":    "#4fc3f7",
        "--accent2":   "#7c4dff",
    },
    "darker": {
        "--bg":        "#000000",
        "--bg-card":   "#0a0a0a",
        "--bg-input":  "#111111",
        "--border":    "#222222",
        "--text":      "#ffffff",
        "--text2":     "#aaaaaa",
        "--text3":     "#444444",
        "--accent":    "#00e5ff",
        "--accent2":   "#aa00ff",
    },
    "light": {
        "--bg":        "#f5f5f5",
        "--bg-card":   "#ffffff",
        "--bg-input":  "#eeeeee",
        "--border":    "#cccccc",
        "--text":      "#111111",
        "--text2":     "#555555",
        "--text3":     "#aaaaaa",
        "--accent":    "#1976d2",
        "--accent2":   "#7b1fa2",
    },
    "hacker": {
        "--bg":        "#000000",
        "--bg-card":   "#001100",
        "--bg-input":  "#001a00",
        "--border":    "#003300",
        "--text":      "#00ff41",
        "--text2":     "#00bb30",
        "--text3":     "#005510",
        "--accent":    "#00ff41",
        "--accent2":   "#00cc33",
    },
    "ocean": {
        "--bg":        "#020c1b",
        "--bg-card":   "#0a192f",
        "--bg-input":  "#112240",
        "--border":    "#1d3557",
        "--text":      "#ccd6f6",
        "--text2":     "#8892b0",
        "--text3":     "#495670",
        "--accent":    "#64ffda",
        "--accent2":   "#57cbff",
    },
}

def _apply_config(config):
    """Apply configuration to index.html — theme, wallpaper, user name."""
    from pathlib import Path
    root = Path(__file__).parent

    html_path = root / "index.html"
    if not html_path.exists():
        return

    content = html_path.read_text(encoding="utf-8")

    # ── Apply API keys to environment ───────────────────────────────
    import os as _os
    for env_key, val in config.get("api_keys", {}).items():
        if val:
            _os.environ[env_key] = val

    # ── Apply theme CSS variables ────────────────────────────────────
    theme_name = config.get("theme", "dark")
    theme = THEMES.get(theme_name, THEMES["dark"])

    # Build CSS variable block
    css_vars = "\n".join(f"    {k}: {v};" for k, v in theme.items())
    theme_block = f"  :root {{\n{css_vars}\n  }}"

    # Replace existing :root block or inject one
    import re
    if re.search(r':root\s*\{[^}]*\}', content):
        content = re.sub(r':root\s*\{[^}]*\}', theme_block.strip(), content, count=1)
    else:
        # Inject before first </style>
        content = content.replace("</style>",
                                  f"\n  {theme_block}\n</style>", 1)

    # ── Apply wallpaper style ────────────────────────────────────────
    wallpaper = config.get("wallpaper", "gradient")
    wp_styles = {
        "gradient":  "background: linear-gradient(135deg, var(--bg) 0%, #0a0a1a 50%, var(--bg) 100%);",
        "minimal":   "background: var(--bg);",
        "particles": "background: var(--bg);",  # JS handles particles
        "none":      "background: var(--bg);",
    }
    wp_css = wp_styles.get(wallpaper, wp_styles["gradient"])

    # ── Inject user name into LUOKAI greeting ───────────────────────
    user_name = config.get("user_name", "")
    if user_name and user_name != "User":
        content = content.replace(
            "I'm LUOKAI — your AI in LuoOS.",
            f"I'm LUOKAI — good to see you, {user_name}."
        )

    # ── Write feature flags as JS constants ─────────────────────────
    features = config.get("features", {})
    feature_js = f"""
  // LuoOS config — generated by setup.py
  const LUOOS_CONFIG = {{
    userName:    {json.dumps(config.get('user_name', 'User'))},
    theme:       {json.dumps(theme_name)},
    wallpaper:   {json.dumps(wallpaper)},
    voiceEnabled: {'true' if features.get('voice', True) else 'false'},
    coevoEnabled: {'true' if features.get('coevo', True) else 'false'},
    neuralEnabled: {'true' if features.get('neural', True) else 'false'},
    autoLearn:   {'true' if features.get('autolearn', True) else 'false'},
  }};"""

    # Replace or inject config block
    if "const LUOOS_CONFIG" in content:
        content = re.sub(
            r'// LuoOS config.*?const LUOOS_CONFIG = \{[^}]+\};',
            feature_js.strip(),
            content, flags=re.DOTALL
        )
    else:
        content = content.replace("const API =", feature_js + "\n  const API =", 1)

    html_path.write_text(content, encoding="utf-8")


# ════════════════════════════════════════════════════════════════════
# PUBLIC API
# ════════════════════════════════════════════════════════════════════

def load_config() -> dict:
    """Load saved config. Returns {} if not set up yet."""
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except Exception:
            return {}
    return {}

def needs_setup() -> bool:
    """True if setup has never been completed."""
    cfg = load_config()
    return not cfg.get("setup_complete", False)

def ensure_setup() -> dict:
    """Run setup if needed, return config either way."""
    if needs_setup():
        return run_setup()
    return load_config()

def reset_setup():
    """Delete config so setup runs again next start."""
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()
    print(f"Config cleared. Run start.py to reconfigure.")

if __name__ == "__main__":
    if "--reset" in sys.argv:
        reset_setup()
    else:
        cfg = run_setup()
        print(json.dumps(cfg, indent=2))
