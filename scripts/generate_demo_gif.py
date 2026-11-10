import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def create_demo_gif():
    os.makedirs("assets", exist_ok=True)
    width, height = 880, 500

    font_bold = "C:/Windows/Fonts/segoeuib.ttf"
    font_reg = "C:/Windows/Fonts/segoeui.ttf"
    font_mono = "C:/Windows/Fonts/consola.ttf"

    title_font = ImageFont.truetype(font_bold, 28)
    sub_font = ImageFont.truetype(font_reg, 15)
    badge_font = ImageFont.truetype(font_bold, 13)
    card_title_font = ImageFont.truetype(font_bold, 15)
    body_font = ImageFont.truetype(font_reg, 14)
    mono_font = ImageFont.truetype(font_mono, 13)
    verdict_font = ImageFont.truetype(font_bold, 22)

    frames = []
    durations = []

    full_claim = "Bananas are naturally radioactive due to potassium-40."
    
    # We will sample typing in chunks
    typing_steps = [
        "",
        "Bananas ",
        "Bananas are ",
        "Bananas are naturally ",
        "Bananas are naturally radioactive ",
        "Bananas are naturally radioactive due to ",
        full_claim,
        full_claim
    ]

    def render_base(claim_text, show_cursor=True, state="typing", progress_step=0, show_share_modal=False):
        img = Image.new("RGBA", (width, height), (9, 12, 18, 255))
        draw = ImageDraw.Draw(img)

        # Ambient glows
        glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        g_draw = ImageDraw.Draw(glow)
        g_draw.ellipse([(-60, -60), (320, 260)], fill=(16, 185, 129, 28))
        g_draw.ellipse([(600, 200), (940, 540)], fill=(6, 182, 212, 22))
        glow = glow.filter(ImageFilter.GaussianBlur(50))
        img = Image.alpha_composite(img, glow)
        draw = ImageDraw.Draw(img)

        # Border
        draw.rounded_rectangle([(8, 8), (width - 8, height - 8)], radius=14, outline=(30, 41, 59, 255), width=1)
        draw.rounded_rectangle([(10, 10), (width - 10, height - 10)], radius=12, outline=(16, 185, 129, 40), width=1)

        # Top Navigation Bar
        draw.rounded_rectangle([(11, 11), (width - 11, 54)], radius=12, fill=(15, 23, 42, 240))
        # Window buttons
        draw.ellipse([(26, 26), (36, 36)], fill=(239, 68, 68))
        draw.ellipse([(44, 26), (54, 36)], fill=(234, 179, 8))
        draw.ellipse([(62, 26), (72, 36)], fill=(34, 197, 94))

        # Brand
        # Shield icon
        sx, sy = 90, 21
        draw.polygon([(sx+9, sy+2), (sx+18, sy+6), (sx+18, sy+15), (sx+9, sy+22), (sx, sy+15), (sx, sy+6)], fill=(16, 185, 129, 255))
        draw.text((sx + 24, sy - 1), "FactGuard AI", font=card_title_font, fill=(248, 250, 252))
        draw.text((sx + 130, sy + 1), "• Live RAG Fact Verification", font=sub_font, fill=(100, 116, 139))

        # Live Server indicator
        draw.ellipse([(width - 165, 27), (width - 157, 35)], fill=(34, 197, 94))
        draw.text((width - 150, 23), "Render Cloud (Live)", font=badge_font, fill=(148, 163, 184))

        # Search / Claim Input Box
        box_y = 70
        is_active = state in ["typing", "streaming"]
        border_col = (16, 185, 129, 200) if is_active else (51, 65, 85, 255)
        draw.rounded_rectangle([(36, box_y), (width - 36, box_y + 54)], radius=10, fill=(2, 6, 23, 240), outline=border_col, width=1)
        
        display_claim = claim_text + ("|" if (show_cursor and state == "typing") else "")
        draw.text((52, box_y + 17), display_claim if display_claim else "Enter any statement to fact-check with live web intelligence...", font=body_font, fill=(241, 245, 249) if display_claim else (100, 116, 139))

        # Action button inside or next to search box
        btn_x = width - 180
        btn_bg = (16, 185, 129, 240) if state != "typing" else (16, 185, 129, 200)
        draw.rounded_rectangle([(btn_x, box_y + 8), (width - 48, box_y + 46)], radius=8, fill=btn_bg)
        draw.text((btn_x + 18, box_y + 17), "Verify Claim ⚡", font=badge_font, fill=(255, 255, 255))

        if state == "typing":
            # Show empty state hints
            hint_y = 150
            draw.text((40, hint_y), "POPULAR CLAIMS TO TEST:", font=badge_font, fill=(100, 116, 139))
            hints = [
                '"Bananas are radioactive due to potassium-40"',
                '"The Great Wall of China is visible from space with the naked eye"',
                '"Honey never spoils and edible honey was found in Egyptian tombs"'
            ]
            hy = hint_y + 26
            for h in hints:
                draw.rounded_rectangle([(40, hy), (draw.textlength(h, font=body_font) + 64, hy + 28)], radius=6, fill=(15, 23, 42, 200), outline=(51, 65, 85, 180), width=1)
                draw.text((52, hy + 5), h, font=body_font, fill=(148, 163, 184))
                hy += 36

        elif state == "streaming":
            # Render real-time progress steps
            prog_y = 145
            draw.text((40, prog_y), "REAL-TIME SSE EVENT PIPELINE", font=badge_font, fill=(100, 116, 139))

            steps = [
                ("1. Claim Decomposition (SpaCy Dependency Parser)", "Isolating atomic verifiable propositions..."),
                ("2. Live Web Retrieval (DuckDuckGo + Wikipedia)", "Querying open web intelligence in real-time..."),
                ("3. BM25Okapi Passage Re-Ranking", "Bi-gram relevance scoring top context passages..."),
                ("4. Multi-LLM Fact Synthesis (Groq LPU / Ollama)", "Reasoning with strict evidence-grounding constraints...")
            ]

            sy = prog_y + 28
            for i, (title, desc) in enumerate(steps):
                is_done = i < progress_step
                is_curr = i == progress_step
                
                if is_done:
                    dot_col = (34, 197, 94)
                    icon = "✓"
                    status_text = "Done"
                elif is_curr:
                    dot_col = (56, 189, 248)
                    icon = "⚡"
                    status_text = "Processing..."
                else:
                    dot_col = (71, 85, 105)
                    icon = "○"
                    status_text = "Queued"

                # Row card
                draw.rounded_rectangle([(40, sy), (width - 40, sy + 44)], radius=8, fill=(15, 23, 42, 220), outline=(dot_col[0], dot_col[1], dot_col[2], 140 if is_curr else 60), width=1)
                draw.text((54, sy + 13), icon, font=badge_font, fill=dot_col)
                draw.text((74, sy + 12), title, font=card_title_font, fill=(248, 250, 252) if (is_done or is_curr) else (148, 163, 184))
                draw.text((450, sy + 14), desc, font=sub_font, fill=(148, 163, 184))
                
                # Status capsule
                draw.rounded_rectangle([(width - 150, sy + 10), (width - 56, sy + 34)], radius=6, fill=(dot_col[0], dot_col[1], dot_col[2], 40))
                draw.text((width - 140, sy + 14), status_text, font=badge_font, fill=dot_col)

                sy += 52

        elif state in ["result", "share"]:
            # Render Verified Result Card
            res_y = 140
            # Result Banner
            draw.rounded_rectangle([(36, res_y), (width - 36, res_y + 60)], radius=12, fill=(6, 78, 59, 220), outline=(16, 185, 129, 255), width=2)
            draw.text((54, res_y + 17), "VERDICT: TRUE", font=verdict_font, fill=(255, 255, 255))
            
            # Confidence Pill
            draw.rounded_rectangle([(230, res_y + 16), (365, res_y + 45)], radius=8, fill=(16, 185, 129, 240))
            draw.text((244, res_y + 22), "95% CONFIDENCE", font=badge_font, fill=(255, 255, 255))

            # Latency Badge
            draw.rounded_rectangle([(380, res_y + 16), (495, res_y + 45)], radius=8, fill=(30, 41, 59, 200), outline=(71, 85, 105, 180), width=1)
            draw.text((392, res_y + 22), "⚡ 2.1s LATENCY", font=badge_font, fill=(56, 189, 248))

            # Action Buttons on Right
            btn_share_x = width - 170
            share_bg = (16, 185, 129, 240) if show_share_modal else (15, 23, 42, 240)
            draw.rounded_rectangle([(btn_share_x, res_y + 14), (width - 50, res_y + 46)], radius=8, fill=share_bg, outline=(16, 185, 129, 255), width=1)
            draw.text((btn_share_x + 14, res_y + 21), "Share Verdict ↗", font=badge_font, fill=(255, 255, 255) if show_share_modal else (110, 231, 183))

            # Reasoning Box
            card_box_y = res_y + 72
            draw.rounded_rectangle([(36, card_box_y), (width - 36, card_box_y + 190)], radius=12, fill=(15, 23, 42, 230), outline=(51, 65, 85, 200), width=1)
            draw.text((52, card_box_y + 14), "VERIFIED REASONING & SYNTHESIS", font=badge_font, fill=(100, 116, 139))
            
            reasoning = (
                "Scientific consensus from radiological health studies and nuclear physics confirms that bananas\n"
                "are naturally radioactive due to the presence of potassium-40 (K-40), a naturally occurring isotope.\n"
                "A standard 150g banana contains roughly 450 mg of potassium, producing approximately 15 Bq\n"
                "of beta and gamma radiation—often referenced in radiation biology as the 'Banana Equivalent Dose' (~0.1 uSv)."
            )
            draw.text((52, card_box_y + 36), reasoning, font=body_font, fill=(226, 232, 240), spacing=5)

            # Citations Pills
            c_y = card_box_y + 138
            draw.text((52, c_y - 20), "AUDITABLE LIVE CITATIONS:", font=badge_font, fill=(100, 116, 139))
            
            draw.rounded_rectangle([(52, c_y), (250, c_y + 30)], radius=6, fill=(30, 41, 59, 240), outline=(71, 85, 105, 200), width=1)
            draw.text((64, c_y + 7), "🔗 Wikipedia (Banana)", font=body_font, fill=(56, 189, 248))

            draw.rounded_rectangle([(262, c_y), (520, c_y + 30)], radius=6, fill=(30, 41, 59, 240), outline=(71, 85, 105, 200), width=1)
            draw.text((274, c_y + 7), "🔗 DuckDuckGo (Banana Equivalent Dose)", font=body_font, fill=(56, 189, 248))

            draw.rounded_rectangle([(532, c_y), (740, c_y + 30)], radius=6, fill=(30, 41, 59, 240), outline=(71, 85, 105, 200), width=1)
            draw.text((544, c_y + 7), "🔗 Nature / Radiological Health", font=body_font, fill=(56, 189, 248))

            # Bottom status
            draw.text((52, height - 26), "Powered by Groq LPU Llama-3.3-70B • 100% Offline Ollama Option • Zero Hallucination Grounding", font=sub_font, fill=(100, 116, 139))

            # Share Modal Overlay
            if show_share_modal:
                # Dim background
                overlay = Image.new("RGBA", (width, height), (0, 0, 0, 170))
                img = Image.alpha_composite(img, overlay)
                draw = ImageDraw.Draw(img)

                # Modal Card
                m_w, m_h = 520, 240
                m_x, m_y = (width - m_w) // 2, (height - m_h) // 2
                draw.rounded_rectangle([(m_x, m_y), (m_x + m_w, m_y + m_h)], radius=14, fill=(15, 23, 42, 255), outline=(16, 185, 129, 220), width=2)
                
                draw.text((m_x + 24, m_y + 18), "Share Verified Verdict", font=title_font.__class__(title_font.path, 18), fill=(248, 250, 252))
                draw.text((m_x + 24, m_y + 44), "Generates dynamic OpenGraph preview card for Twitter, Reddit, and LinkedIn", font=sub_font, fill=(148, 163, 184))

                # Permalink Box
                draw.rounded_rectangle([(m_x + 24, m_y + 75), (m_x + m_w - 24, m_y + 115)], radius=8, fill=(2, 6, 23, 240), outline=(51, 65, 85, 240), width=1)
                draw.text((m_x + 36, m_y + 87), "https://factguard-1gge.onrender.com/v/f3eeb5", font=mono_font, fill=(110, 231, 183))
                # Copy button
                draw.rounded_rectangle([(m_x + m_w - 110, m_y + 80), (m_x + m_w - 30, m_y + 110)], radius=6, fill=(16, 185, 129, 240))
                draw.text((m_x + m_w - 96, m_y + 87), "Copied! ✓", font=badge_font, fill=(255, 255, 255))

                # Social buttons
                soc_y = m_y + 135
                draw.rounded_rectangle([(m_x + 24, soc_y), (m_x + 160, soc_y + 36)], radius=6, fill=(29, 155, 240, 40), outline=(29, 155, 240, 160), width=1)
                draw.text((m_x + 38, soc_y + 9), "Share to X / Twitter", font=badge_font, fill=(56, 189, 248))

                draw.rounded_rectangle([(m_x + 172, soc_y), (m_x + 310, soc_y + 36)], radius=6, fill=(255, 69, 0, 40), outline=(255, 69, 0, 160), width=1)
                draw.text((m_x + 188, soc_y + 9), "Share to Reddit", font=badge_font, fill=(251, 146, 60))

                draw.rounded_rectangle([(m_x + 322, soc_y), (m_x + 480, soc_y + 36)], radius=6, fill=(16, 185, 129, 40), outline=(16, 185, 129, 160), width=1)
                draw.text((m_x + 338, soc_y + 9), "Copy Markdown Badge", font=badge_font, fill=(110, 231, 183))

                draw.text((m_x + 24, m_y + m_h - 32), "OpenGraph image preview dynamically generated at /api/og/f3eeb5.svg", font=mono_font, fill=(100, 116, 139))

        return img.convert("RGB")

    print("Generating demo frames...")

    # Phase 1: Typing
    for text in typing_steps:
        frames.append(render_base(text, show_cursor=True, state="typing"))
        durations.append(180)
    
    # Hold full claim for 400ms
    frames.append(render_base(full_claim, show_cursor=False, state="typing"))
    durations.append(400)

    # Phase 2: Streaming stages (0, 1, 2, 3)
    for step in range(4):
        frames.append(render_base(full_claim, state="streaming", progress_step=step))
        durations.append(600)
    
    # Phase 3: Result Reveal
    for _ in range(6):
        frames.append(render_base(full_claim, state="result", show_share_modal=False))
        durations.append(400)

    # Phase 4: Share Modal Opens
    for _ in range(6):
        frames.append(render_base(full_claim, state="share", show_share_modal=True))
        durations.append(450)

    # Final hold on Result Card
    for _ in range(6):
        frames.append(render_base(full_claim, state="result", show_share_modal=False))
        durations.append(400)

    out_gif = "assets/demo.gif"
    print(f"Compiling {len(frames)} frames into {out_gif}...")
    frames[0].save(
        out_gif,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True
    )
    print(f"Successfully generated {out_gif} ({os.path.getsize(out_gif) / 1024:.1f} KB)!")

if __name__ == "__main__":
    create_demo_gif()

