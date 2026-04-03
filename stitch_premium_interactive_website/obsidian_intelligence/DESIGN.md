# Design System Specification: Editorial Intelligence

## 1. Overview & Creative North Star
The Creative North Star for this design system is **"The Digital Architect."** 

Unlike standard SaaS platforms that feel like "software tools," this system is designed to feel like a high-end technical journal or a premium architectural blueprint. We are moving away from the "boxy" nature of traditional dashboards toward a fluid, editorial experience. 

The system breaks the "template" look through **Intentional Asymmetry** and **Tonal Depth**. By utilizing high-contrast typography scales (the tension between a modern sans and a classic serif) and layered obsidian surfaces, we create an environment that feels both cutting-edge and deeply authoritative. We don't just display code; we curate understanding.

---

## 2. Colors: The Obsidian Palette
The color strategy relies on a "black-on-black" layering technique to create a sense of infinite depth.

### Core Tones
- **Background (`#0d0e10`):** Our foundation. A deep obsidian that provides a void for our intelligence to glow within.
- **Neural Violet (`primary`: `#b6a0ff`):** Used sparingly as a high-energy pulse. This represents the "spark" of AI comprehension.
- **Subtle Slate (`secondary`: `#d7e4ec`):** Used for supporting information to keep the UI from feeling monochromatic.

### The "No-Line" Rule
**Explicit Instruction:** Prohibit the use of 1px solid borders for sectioning content. 
Structure must be defined solely through background color shifts. To separate a sidebar from a main content area, transition from `surface` to `surface-container-low`. To highlight a code block, use `surface-container-high`. We define boundaries through mass and tone, not through lines.

### The "Glass & Gradient" Rule
To elevate main CTAs and hero sections, use linear gradients transitioning from `primary` (#b6a0ff) to `primary-dim` (#7e51ff). For floating overlays, apply Glassmorphism:
- **Surface:** `surface-container` at 60% opacity.
- **Blur:** 20px - 40px backdrop-blur.
- **Effect:** This allows the "Neural Violet" accents of the background to bleed through, creating an integrated, organic feel.

---

## 3. Typography: Technical Editorial
We embrace a dual-typeface system to represent the duality of the product: Expert Wisdom (Serif) and Technical Precision (Sans).

- **Display & Headlines (Newsreader):** Used for "Brand Moments." The high-stroke contrast of Newsreader adds an editorial, trustworthy weight to high-level insights.
- **Title, Body, & Labels (Inter):** Used for "Functional Moments." Inter provides the clinical clarity required for reading complex code structures and metadata.

**Hierarchy as Identity:**
- **`display-lg` (3.5rem):** Reserved for hero value propositions.
- **`title-md` (1.125rem):** The workhorse for technical headers.
- **`label-sm` (0.6875rem):** Used for metadata and code annotations, always set in `on-surface-variant` to maintain a quiet, secondary presence.

---

## 4. Elevation & Depth: Tonal Layering
In this design system, "Up" is "Brighter." We do not use traditional drop shadows to signify elevation; we use light.

### The Layering Principle
Stack surfaces to create a natural "lift":
1. **Base:** `surface` (#0d0e10)
2. **Section:** `surface-container-low` (#121316)
3. **Card/Element:** `surface-container-highest` (#242629)

### Ambient Shadows
If an element must float (e.g., a dropdown or a modal), use a "Neural Glow." 
- **Shadow:** 0px 20px 50px rgba(182, 160, 255, 0.08). 
- This shadow is tinted with our `primary` color, making the light feel like it's being emitted by the AI engine itself.

### The "Ghost Border" Fallback
If accessibility requires a container edge, use the **Ghost Border**: `outline-variant` (#47484a) at **15% opacity**. It should be felt, not seen.

---

## 5. Components

### Buttons: The Kinetic Pulse
- **Primary:** Gradient fill (`primary` to `primary-dim`). Border-radius: `md` (0.375rem). No border. On hover, increase the `surface-tint` glow.
- **Secondary:** Transparent fill with a `Ghost Border`. Text set in `primary`.
- **Tertiary:** No fill, no border. `label-md` weight. Used for low-priority actions.

### Cards & Lists: The Separation Principle
**Forbid the use of divider lines.** 
Separate list items using `12px` of vertical white space or a subtle hover state shift to `surface-container-high`. Cards should utilize `surface-container-low` with a slightly more aggressive corner radius (`xl`: 0.75rem) to feel like modern hardware modules.

### Input Fields: Focus States
- **Resting:** `surface-container-highest` fill. No border.
- **Focus:** A 1px "Neural Violet" (`primary`) glow effect using `box-shadow`. The text cursor should also be `primary`.

### Neural Chips
Small, pill-shaped (`full` radius) elements used for code tags. Use `surface-container-high` background with `on-surface-variant` text. When active, shift to a `primary-container` background with `on-primary-container` text.

### Interactive Code Blocks
A custom component for this system. Use `surface-container-lowest` (#000000) for the background to provide maximum contrast for syntax highlighting. Use a `sm` (0.125rem) radius for a "technical/sharp" feel.

---

## 6. Do's and Don'ts

### Do
- **Do** use whitespace as a structural element. If an interface feels cluttered, increase the gap between tonal shifts rather than adding a line.
- **Do** use the serif `Newsreader` font for any text that is meant to be read as an "insight" or "conclusion" generated by the AI.
- **Do** ensure that all glassmorphic elements have sufficient backdrop-blur (minimum 16px) to maintain text legibility.

### Don't
- **Don't** use pure white (#FFFFFF) for text. Always use `on-surface` (#fdfbfe) to reduce eye strain in the dark environment.
- **Don't** use "standard" blue for links. Every interactive element must stem from the `primary` (Violet) or `tertiary` (Teal) palettes.
- **Don't** use heavy, opaque shadows. If the shadow looks like a "smudge," it is too dark. It should look like "ambient light."
- **Don't** use the serif font for technical labels or code; it is strictly for high-level editorial storytelling.