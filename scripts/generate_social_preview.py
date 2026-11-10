import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def create_social_preview():
    os.makedirs("assets", exist_ok=True)
    width, height = 1280, 640
    img = Image.new("RGBA", (width, height), (7, 9, 14, 255))
    draw = ImageDraw.Draw(img)

    # 1. Background radial ambient glows
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    
    # Emerald glow top-left
    glow_draw.ellipse([(-100, -100), (500, 450)], fill=(16, 185, 129, 35))
    # Cyan glow bottom-right
    glow_draw.ellipse([(800, 250), (1400, 750)], fill=(6, 182, 212, 30))
    # Subtle purple accent center-right
    glow_draw.ellipse([(950, -50), (1350, 350)], fill=(99, 102, 241, 20))
    
    glow = glow.filter(ImageFilter.GaussianBlur(80))
    img = Image.alpha_composite(img, glow)
    draw = ImageDraw.Draw(img)

    # 2. Subtle cyber grid dots
    for x in range(30, width, 40):
        for y in range(30, height, 40):
            draw.point((x, y), fill=(255, 255, 255, 12))

    # Outer border accent
    draw.rounded_rectangle([(16, 16), (width - 16, height - 16)], radius=20, outline=(30, 41, 59, 255), width=2)
    draw.rounded_rectangle([(18, 18), (width - 18, height - 18)], radius=18, outline=(16, 185, 129, 50), width=1)

    # Load Fonts
    font_bold = "C:/Windows/Fonts/segoeuib.ttf"
    font_reg = "C:/Windows/Fonts/segoeui.ttf"
    font_mono = "C:/Windows/Fonts/consola.ttf"

    title_font = ImageFont.truetype(font_bold, 46)
    sub_font = ImageFont.truetype(font_reg, 21)
    badge_font = ImageFont.truetype(font_bold, 14)
    card_title_font = ImageFont.truetype(font_bold, 16)
    body_font = ImageFont.truetype(font_reg, 15)
    mono_font = ImageFont.truetype(font_mono, 14)
    feat_title_font = ImageFont.truetype(font_bold, 18)
    feat_sub_font = ImageFont.truetype(font_reg, 14)

    # 3. Header Section (Top Left)
    # Shield Icon drawing
    shield_x, shield_y = 60, 48
    # Shield glow
    draw.ellipse([(shield_x - 10, shield_y - 10), (shield_x + 52, shield_y + 54)], fill=(16, 185, 129, 45))
    draw.polygon([
        (shield_x + 21, shield_y + 2),
        (shield_x + 39, shield_y + 11),
        (shield_x + 39, shield_y + 30),
        (shield_x + 21, shield_y + 44),
        (shield_x + 3, shield_y + 30),
        (shield_x + 3, shield_y + 11)
    ], fill=(16, 185, 129, 230), outline=(52, 211, 153, 255))
    # Checkmark inside shield
    draw.line([(shield_x + 12, shield_y + 22), (shield_x + 18, shield_y + 29)], fill=(255, 255, 255), width=3)
    draw.line([(shield_x + 18, shield_y + 29), (shield_x + 30, shield_y + 16)], fill=(255, 255, 255), width=3)

    # Logo Text
    draw.text((shield_x + 54, shield_y - 4), "FactGuard", font=title_font, fill=(248, 250, 252))
    w_title = draw.textlength("FactGuard", font=title_font)
    draw.text((shield_x + 54 + w_title + 8, shield_y - 4), "AI", font=title_font, fill=(52, 211, 153))

    # Version / Release Pill
    pill_x = shield_x + 54 + w_title + 80
    pill_y = shield_y + 10
    draw.rounded_rectangle([(pill_x, pill_y), (pill_x + 145, pill_y + 26)], radius=13, fill=(16, 185, 129, 30), outline=(16, 185, 129, 120), width=1)
    draw.text((pill_x + 14, pill_y + 4), "v1.1 • MIT LICENSE", font=badge_font, fill=(110, 231, 183))

    # Subtitle
    draw.text((60, 110), "Real-Time Web Intelligence & Multi-LLM Fact Verification Engine", font=sub_font, fill=(148, 163, 184))

    # 4. Left Card: The Interactive Verification Mockup (Glassmorphism)
    card_x, card_y = 60, 160
    card_w, card_h = 580, 420

    # Glass background
    draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], radius=16, fill=(15, 23, 42, 210), outline=(51, 65, 85, 255), width=1)
    # Header bar
    draw.rounded_rectangle([(card_x + 1, card_y + 1), (card_x + card_w - 1, card_y + 46)], radius=15, fill=(30, 41, 59, 160))
    # Window traffic lights
    draw.ellipse([(card_x + 18, card_y + 18), (card_x + 28, card_y + 28)], fill=(239, 68, 68))
    draw.ellipse([(card_x + 36, card_y + 18), (card_x + 46, card_y + 28)], fill=(234, 179, 8))
    draw.ellipse([(card_x + 54, card_y + 18), (card_x + 64, card_y + 28)], fill=(34, 197, 94))
    draw.text((card_x + 80, card_y + 14), "factguard-agent // live-stream-verification", font=mono_font, fill=(148, 163, 184))

    # Claim Input Box
    box_y = card_y + 60
    draw.rounded_rectangle([(card_x + 20, box_y), (card_x + card_w - 20, box_y + 54)], radius=10, fill=(2, 6, 23, 230), outline=(71, 85, 105, 200), width=1)
    draw.text((card_x + 32, box_y + 8), "CLAIM TO VERIFY", font=badge_font, fill=(100, 116, 139))
    draw.text((card_x + 32, box_y + 26), '"Bananas are naturally radioactive due to potassium-40."', font=body_font, fill=(241, 245, 249))

    # Pipeline SSE Streaming Badges
    pipe_y = box_y + 68
    phases = [
        ("✓ Claim Decomp", (34, 197, 94)),
        ("✓ Live Search", (34, 197, 94)),
        ("✓ BM25 Re-Rank", (34, 197, 94)),
        ("✓ Groq/Ollama", (56, 189, 248)),
    ]
    cur_px = card_x + 20
    for title, col in phases:
        w_p = draw.textlength(title, font=badge_font) + 20
        draw.rounded_rectangle([(cur_px, pipe_y), (cur_px + w_p, pipe_y + 24)], radius=6, fill=(15, 23, 42, 255), outline=col, width=1)
        draw.text((cur_px + 10, pipe_y + 4), title, font=badge_font, fill=col)
        cur_px += w_p + 10

    # Verdict Banner
    v_y = pipe_y + 36
    draw.rounded_rectangle([(card_x + 20, v_y), (card_x + card_w - 20, v_y + 64)], radius=12, fill=(6, 78, 59, 180), outline=(16, 185, 129, 255), width=2)
    # Shield inside verdict
    draw.text((card_x + 36, v_y + 16), "VERDICT: TRUE", font=title_font.__class__(title_font.path, 24), fill=(255, 255, 255))
    # Confidence capsule
    conf_x = card_x + card_w - 180
    draw.rounded_rectangle([(conf_x, v_y + 16), (conf_x + 145, v_y + 48)], radius=8, fill=(16, 185, 129, 220))
    draw.text((conf_x + 14, v_y + 22), "95% CONFIDENCE", font=badge_font, fill=(255, 255, 255))

    # Synthesized Rationale Snippet
    r_y = v_y + 76
    reasoning_text = (
        "Grounding: Analysis of live Wikipedia and scientific consensus confirms that bananas\n"
        "contain naturally occurring potassium-40 (K-40), emitting low-level ionizing radiation\n"
        "measured at ~0.1 uSv (one Banana Equivalent Dose)."
    )
    draw.text((card_x + 24, r_y), reasoning_text, font=body_font, fill=(203, 213, 225), spacing=4)

    # Citation Pills Footer
    cit_y = card_y + card_h - 48
    draw.rounded_rectangle([(card_x + 20, cit_y), (card_x + 180, cit_y + 30)], radius=8, fill=(30, 41, 59, 200), outline=(71, 85, 105, 180), width=1)
    draw.text((card_x + 32, cit_y + 6), "🔗 Wikipedia (Banana)", font=body_font, fill=(56, 189, 248))

    draw.rounded_rectangle([(card_x + 195, cit_y), (card_x + 390, cit_y + 30)], radius=8, fill=(30, 41, 59, 200), outline=(71, 85, 105, 180), width=1)
    draw.text((card_x + 207, cit_y + 6), "🔗 DuckDuckGo (K-40 Radiation)", font=body_font, fill=(56, 189, 248))

    # Share pill
    draw.rounded_rectangle([(card_x + card_w - 145, cit_y), (card_x + card_w - 20, cit_y + 30)], radius=8, fill=(16, 185, 129, 40), outline=(16, 185, 129, 200), width=1)
    draw.text((card_x + card_w - 130, cit_y + 6), "Share /v/:id ↗", font=body_font, fill=(110, 231, 183))


    # 5. Right Column: Key Architecture Pillars & Distribution Highlights
    col_x = 680
    feat_y = 160

    features = [
        ("🌐 Live Internet RAG", "Concurrent DuckDuckGo & Wikipedia search. Zero stale vector databases.", (56, 189, 248)),
        ("⚡ BM25Okapi Relevance Re-Ranking", "Bi-gram algorithmic passage scoring with sub-millisecond latency.", (52, 211, 153)),
        ("🦙 100% Local Offline AI (Ollama)", "Zero cloud keys. Works natively with Gemma 4, Llama 3.2, and Mistral.", (251, 146, 60)),
        ("⚡ Groq LPU Inference (500+ tok/s)", "Instant claim synthesis & multi-turn streaming over Server-Sent Events.", (244, 114, 182)),
        ("🧩 Chrome Browser Extension Companion", "Highlight any text on Twitter, Reddit, or news -> instant 1-click verification.", (167, 139, 250)),
        ("📦 Standalone Python Package", "pip install factguard for terminal scripts, custom agents, and RAG pipelines.", (250, 204, 21)),
    ]

    for title, desc, icon_col in features:
        # Icon dot
        draw.ellipse([(col_x, feat_y + 4), (col_x + 12, feat_y + 16)], fill=icon_col)
        draw.text((col_x + 24, feat_y), title, font=feat_title_font, fill=(248, 250, 252))
        draw.text((col_x + 24, feat_y + 24), desc, font=feat_sub_font, fill=(148, 163, 184))
        feat_y += 68

    # Bottom pill badges on the right
    pills_y = 572
    tech_tags = ["Python 3.11", "FastAPI", "Next.js", "Ollama", "Groq", "Docker", "Manifest V3"]
    cur_tx = col_x
    for tag in tech_tags:
        w_t = draw.textlength(tag, font=badge_font) + 16
        draw.rounded_rectangle([(cur_tx, pills_y), (cur_tx + w_t, pills_y + 24)], radius=6, fill=(30, 41, 59, 180), outline=(51, 65, 85, 200), width=1)
        draw.text((cur_tx + 8, pills_y + 4), tag, font=badge_font, fill=(148, 163, 184))
        cur_tx += w_t + 8

    # Save PNG
    out_path = "assets/social-preview.png"
    img.save(out_path, format="PNG", optimize=True)
    print(f"Generated {out_path} ({width}x{height}) successfully!")

if __name__ == "__main__":
    create_social_preview()

