# ResumeV2 Design Library

**Purpose:** A source-derived reference for extending the public portfolio’s visual language. This is documentation, not a component API or executable token file.

## Source and confidence

The active public entry imports styles in this order: `tokens.css`, `animations.css`, `globals.css`, then `editorial.css`. The last file deliberately overrides portions of the older global stylesheet, so read the cascade rather than treating an earlier declaration as the rendered value. Route CSS Modules add focused composition rules.

The current font imports in `tokens.css` are Satoshi and Newsreader. The local prose in `docs/design-system.md` names an earlier DM font setup; this document follows the imported CSS. The token `--mono` currently aliases Satoshi. Photography collection themes may choose a real system monospace or another curated fallback.

Values marked confirmed are directly declared in source. Inferred values describe recurring practice where the application has no explicit token or universal rule. JSON objects are reference descriptions; the application does not consume them.

Primary source files:

- `client/src/styles/tokens.css`
- `client/src/styles/globals.css`
- `client/src/styles/editorial.css`
- `client/src/styles/animations.css`
- `client/src/main.tsx`
- `client/src/components/Navigation.tsx` and `Navigation.module.css`
- `client/src/components/common.tsx`
- `client/src/components/Home.tsx` and `Home.module.css`
- `client/src/components/Work.tsx` and `Work.module.css`
- `client/src/components/Projects.tsx`, `ProjectCard.tsx`, `ProjectDetail.tsx`, and `ProjectDetail.module.css`
- `client/src/components/Photography.tsx`, `PhotographyCollection.tsx`, `PhotoCard.tsx`, `PhotoCard.module.css`, `Photography.module.css`, and `PhotographyCollection.module.css`
- `client/src/components/About.tsx` and `About.module.css`
- `client/src/components/Food.tsx`, `RecipeCard.tsx`, `RecipeDetail.tsx`, and `RecipeDetail.module.css`
- `client/src/components/Contact.tsx` and `Contact.module.css`
- `client/src/components/Footer.tsx` and `Footer.module.css`
- `client/src/media-position.ts`
- `shared/types/src/index.ts` for photography themes and public media labels

## 1. Design overview

The site is an editorial portfolio with a quiet, warm-gray paper foundation. It uses large, close-set sans-serif headings for page identity, Newsreader for selected expressive copy and card titles, and ample open space around image-led content. Most pages are restrained: a tinted paper surface, dark text, fine rules, one route accent, and little or no rounding. Expression concentrates in the content itself: oversized titles, asymmetric columns, gently tilted photo-paper frames, project and collection cards with crisp offset shadows, and distinct image sequences.

Content density changes by purpose. Home is a spacious opening spread with a large portrait and a narrow discipline index; Work is a compact ruled list; Projects pairs a lead preview with denser list rows; Photography gives images more area and offers several archive/gallery arrangements; Food uses staggered image previews and a practical recipe layout; Contact balances direct links with a bordered form. Navigation and footer remain shared across the routes. Interactions are short and directional: a route-colored underline, slight translation, image zoom, or hard-shadow shift makes affordance visible without turning the interface into a motion showcase.

```json
{
  "designIdentity": {
    "tone": ["editorial", "personal", "image-led", "quietly tactile", "restrained"],
    "principles": [
      "Use a shared neutral paper and charcoal foundation; apply route colors as accents and subtle surface tints.",
      "Let large Satoshi headings establish hierarchy, with Newsreader reserved for selected editorial emphasis.",
      "Give content generous breathing room, then let lists and metadata become compact where the content benefits from scanning.",
      "Use photography as authored content with deliberate crops, frames, and captions rather than decorative filler.",
      "Keep global chrome stable while allowing route and collection compositions to differ."
    ],
    "avoid": [
      "Uniform rounded cards, pill labels, and repeated dashboard-like grids.",
      "Replacing the restrained route tint with a full saturated page palette.",
      "Adding decorative indexes, technical ornaments, or backgrounds without a source precedent.",
      "Treating Work rows, Project previews, and Photography collections as interchangeable card components.",
      "Applying expressive shadows or rotation to every surface."
    ]
  }
}
```

## 2. Global tokens

The palette is tokenized, but not every meaningful color is a standalone swatch: route surfaces use CSS `color-mix()` expressions. Preserve those relationships so light and dark modes remain coherent. The footer stays a dark contrast surface in both themes.

```json
{
  "sourceConfidence": "confirmed",
  "sourceFiles": ["client/src/styles/tokens.css", "client/src/styles/globals.css", "client/src/styles/editorial.css"],
  "colors": {
    "light": {
      "background": {"token": "--paper", "value": "#f1f2ef"},
      "backgroundDeep": {"token": "--paper-deep", "value": "#dfe4e2"},
      "surface": {"token": "--surface", "value": "#f8f9f5"},
      "surfaceRaised": {"token": "--surface-raised", "value": "#fdfdf9"},
      "surfaceMuted": {"token": "--surface-muted", "value": "#e8e8e2"},
      "navigationSurface": {"token": "--nav-surface", "value": "#e7e8e4"},
      "textPrimary": {"token": "--ink", "value": "#24241f"},
      "textSecondary": {"token": "--ink-soft", "value": "#66645d"},
      "textFaint": {"token": "--ink-faint", "value": "rgba(36, 36, 31, 0.07)"},
      "border": {"token": "--line", "value": "rgba(36, 36, 31, 0.18)"},
      "borderStrong": {"token": "--line-strong", "value": "rgba(36, 36, 31, 0.5)"},
      "focus": {"token": "--focus", "value": "#2458a6"},
      "copper": {"token": "--copper", "value": "#b44c30"},
      "copperDark": {"token": "--copper-dark", "value": "#823528"},
      "electricBlue": {"token": "--electric-blue", "value": "#2458a6"},
      "homeSurface": {"token": "--home-page-surface", "value": "color-mix(in srgb, var(--paper) 96%, #ecefee)"},
      "homeAccent": {"token": "--home-page-accent", "value": "#193f64"},
      "workSurface": {"token": "--work-page-surface", "value": "color-mix(in srgb, var(--paper) 92%, #b8ccdc)"},
      "workAccent": {"token": "--work-page-accent", "value": "#193f64"},
      "projectsSurface": {"token": "--projects-page-surface", "value": "color-mix(in srgb, var(--paper) 92%, #d1dfcb)"},
      "projectsAccent": {"token": "--projects-page-accent", "value": "#315b42"},
      "photographySurface": {"token": "--photography-page-surface", "value": "color-mix(in srgb, var(--paper) 92%, #d6aaa7)"},
      "photographyAccent": {"token": "--photography-page-accent", "value": "#72283a"},
      "foodSurface": {"token": "--food-page-surface", "value": "color-mix(in srgb, var(--paper) 92%, #ecd3bc)"},
      "foodAccent": {"token": "--food-page-accent", "value": "#823528"},
      "aboutSurface": {"token": "--about-page-surface", "value": "color-mix(in srgb, var(--paper) 94%, #e7ece3)"},
      "aboutAccent": {"token": "--about-page-accent", "value": "#72283a"},
      "contactSurface": {"token": "--contact-page-surface", "value": "color-mix(in srgb, var(--paper) 92%, #e7dcb2)"},
      "contactAccent": {"token": "--contact-page-accent", "value": "#c48d15"},
      "contactAccentInk": {"token": "--contact-accent-ink", "value": "#24241f"},
      "footerSurface": {"token": "--footer-surface", "value": "#20231f"},
      "footerText": {"token": "--footer-ink", "value": "#f4efe5"},
      "footerTextSoft": {"token": "--footer-ink-soft", "value": "#b9b9af"},
      "footerBorder": {"token": "--footer-border", "value": "rgba(244, 239, 229, 0.18)"},
      "photoPaper": {"token": "--photo-paper", "value": "#fffdf8"},
      "photoInk": {"token": "--photo-ink", "value": "#292a27"},
      "statusArchived": {"tokens": ["--project-status-archived-color", "--project-status-archived-surface"], "values": ["#a96f00", "#f0cd70"]},
      "statusInProgress": {"tokens": ["--project-status-progress-color", "--project-status-progress-surface"], "values": ["#477f9f", "#c6e0f0"]}
    },
    "dark": {
      "background": {"token": "--paper", "value": "#22231f"},
      "backgroundDeep": {"token": "--paper-deep", "value": "#2d2e29"},
      "surface": {"token": "--surface", "value": "#292a26"},
      "surfaceRaised": {"token": "--surface-raised", "value": "#30312c"},
      "surfaceMuted": {"token": "--surface-muted", "value": "#292a26"},
      "navigationSurface": {"token": "--nav-surface", "value": "#292a27"},
      "textPrimary": {"token": "--ink", "value": "#eee8dd"},
      "textSecondary": {"token": "--ink-soft", "value": "#b4aea3"},
      "textFaint": {"token": "--ink-faint", "value": "rgba(238, 232, 221, 0.07)"},
      "border": {"token": "--line", "value": "rgba(238, 232, 221, 0.17)"},
      "borderStrong": {"token": "--line-strong", "value": "rgba(238, 232, 221, 0.42)"},
      "focus": {"token": "--focus", "value": "#9abbe0"},
      "copper": {"token": "--copper", "value": "#d27759"},
      "copperDark": {"token": "--copper-dark", "value": "#dc8a72"},
      "electricBlue": {"token": "--electric-blue", "value": "#78a3d2"},
      "homeSurface": {"token": "--home-page-surface", "value": "color-mix(in srgb, var(--paper) 96%, #232522)"},
      "homeAccent": {"token": "--home-page-accent", "value": "#8eafd0"},
      "workSurface": {"token": "--work-page-surface", "value": "color-mix(in srgb, var(--paper) 92%, #242828)"},
      "workAccent": {"token": "--work-page-accent", "value": "#8eafd0"},
      "projectsSurface": {"token": "--projects-page-surface", "value": "color-mix(in srgb, var(--paper) 92%, #282a22)"},
      "projectsAccent": {"token": "--projects-page-accent", "value": "#a4ac7f"},
      "photographySurface": {"token": "--photography-page-surface", "value": "color-mix(in srgb, var(--paper) 92%, #282623)"},
      "photographyAccent": {"token": "--photography-page-accent", "value": "#c47070"},
      "foodSurface": {"token": "--food-page-surface", "value": "color-mix(in srgb, var(--paper) 92%, #332d27)"},
      "foodAccent": {"token": "--food-page-accent", "value": "#dc8a72"},
      "aboutSurface": {"token": "--about-page-surface", "value": "color-mix(in srgb, var(--paper) 94%, #252722)"},
      "aboutAccent": {"token": "--about-page-accent", "value": "#b66b7c"},
      "contactSurface": {"token": "--contact-page-surface", "value": "color-mix(in srgb, var(--paper) 92%, #23211d)"},
      "contactAccent": {"token": "--contact-page-accent", "value": "#dbb33c"},
      "footerSurface": {"token": "--footer-surface", "value": "#171916"},
      "footerText": {"token": "--footer-ink", "value": "#f4eee4"},
      "footerTextSoft": {"token": "--footer-ink-soft", "value": "#acaea6"},
      "footerBorder": {"token": "--footer-border", "value": "rgba(244, 238, 228, 0.17)"},
      "photoPaper": {"token": "--photo-paper", "value": "#d8d2c7"},
      "photoInk": {"token": "--photo-ink", "value": "#292a27"}
    }
  },
  "typography": {
    "display": {"fontFamily": "var(--sans) = Satoshi, Helvetica Neue, Arial, sans-serif", "weight": "400–600 by composition", "size": "route-specific clamp() values; Home hero clamp(4.25rem, 8vw, 8.5rem)", "lineHeight": "0.88–0.98 for display headings", "letterSpacing": "-0.045em to -0.075em"},
    "body": {"fontFamily": "var(--sans) = Satoshi, Helvetica Neue, Arial, sans-serif", "weight": "400", "size": "16px desktop; 15px at max-width 680px", "lineHeight": "1.62 editorial layer"},
    "editorial": {"fontFamily": "var(--serif) = Newsreader, Georgia, serif", "use": "Selected h2/h3 emphasis, card titles, prose statements, photo captions, and recipe section titles"},
    "metadata": {"fontFamily": "var(--mono) aliases var(--sans) in the shared token file", "commonSize": "0.58rem–0.74rem", "letterSpacing": "typically 0.06em–0.105em", "capitalization": "Often uppercase for kickers, status, compact metadata; not universal"},
    "responsiveScale": "Use clamp() on large type. Route h1 values vary; Photography and Projects use distinct mobile title sizes."
  },
  "spacing": {
    "formalScale": false,
    "sourceConfidence": "inferred from recurring source values",
    "xs": "0.4rem–0.65rem recurring control and label gaps",
    "sm": "0.75rem–1rem recurring compact spacing",
    "md": "1.25rem–2rem recurring component spacing",
    "lg": "2.5rem–4rem recurring composition gaps",
    "xl": "5rem–8rem recurring large section spacing",
    "gutter": {"token": "--gutter", "value": "clamp(1.25rem, 4.2vw, 4.75rem); max-width 900px uses 1.5rem; max-width 680px resolves to 1.25rem"},
    "section": {"token": "--section-space", "value": "clamp(4rem, 7vw, 7rem)"},
    "sectionLarge": {"token": "--section-space-large", "value": "clamp(5rem, 9vw, 9rem)"}
  },
  "layoutTokens": {
    "maxContentWidth": {"token": "--max", "value": "1320px"},
    "maxReadingWidth": {"token": "--text-max", "value": "68ch"},
    "easing": {"token": "--ease", "value": "cubic-bezier(0.22, 0.61, 0.36, 1)"},
    "easingOut": {"token": "--ease-out", "value": "cubic-bezier(0.16, 1, 0.3, 1)"}
  },
  "borders": {
    "default": "1px solid var(--line)",
    "strong": "1px solid var(--line-strong)",
    "interactive": "Route accent underlines and borders; square corners in most controls",
    "image": "Usually no border on shared MediaFrame; context-specific border is added for project list and photo themes"
  },
  "radii": {
    "system": "No shared rounded-card radius; most surfaces and controls use border-radius: 0",
    "exceptions": ["Circular 2.15rem RS mark", "Small circular status dots and recipe-mode dot"]
  },
  "shadows": {
    "soft": {"token": "--shadow-offset", "light": "0 12px 34px rgba(36, 36, 31, 0.08)", "dark": "0 14px 38px rgba(0, 0, 0, 0.16)", "use": "Subtle separation; not the default for every panel"},
    "hardEditorial": "Small crisp offsets are an authored card treatment: typically 6px 6px 0, rising to 10px 10px 0 on hover.",
    "photoPaper": "Home/Work Polaroid uses 0.75rem 1rem 2.5rem rgba(36, 36, 31, 0.14).",
    "rule": "Prefer line or no shadow for ordinary content blocks."
  }
}
```

### Typography hierarchy

The large headings are a shared voice but not a fixed scale. Satoshi carries every standard page H1. Newsreader adds contrast in selected sections and cards; it does not replace the page-title voice. Kicker text is small, uppercase, letter-spaced, and often colored by the route. Body copy is muted gray when secondary, with the normal ink reserved for primary copy. Photography themes can deliberately override type on a collection and its gallery only.

## 3. Page shell

The shell is a centered `.container` constrained to 1320px with responsive outer gutters. The header is sticky and spans the viewport; its inner row follows the container. Each route composition sits below it, with a shared footer after route content. Most pages use large top padding on their introduction and large bottom padding for major sections. The Home hero is the exception: it is sized against the viewport and concludes with its own discipline index.

```json
{
  "component": "PageShell",
  "purpose": "Provide a stable frame for route content, persistent navigation, and the shared footer.",
  "sourceFiles": ["client/src/main.tsx", "client/src/App.tsx", "client/src/styles/globals.css", "client/src/styles/editorial.css", "client/src/styles/tokens.css"],
  "sourceConfidence": "confirmed",
  "anatomy": ["sticky site header", "route frame", "route composition", "shared footer"],
  "layout": {
    "maxWidth": "var(--max) = 1320px",
    "paddingInline": "var(--gutter) on .container; clamp(1.25rem, 4.2vw, 4.75rem) before breakpoint overrides",
    "paddingBlock": "Large page introductions commonly use clamp(6rem, 11vw, 11rem) top and clamp(4rem, 8vw, 8rem) bottom; section spacing uses --section-space and --section-space-large",
    "headerBehavior": "Sticky at top: 0 with z-index 20; route accent follows the enabled route; remains ruled at all scroll positions.",
    "footerBehavior": "Shared after route content; dark surface; conversational CTA appears when Contact is enabled."
  },
  "responsive": {
    "900px": "Outer gutter narrows to 1.5rem.",
    "680px": "Gutter becomes 1.25rem; route grids generally stack; header compacts.",
    "routeFrame": "At least 60vh in the base route boundary; page shell itself is min-height 100vh."
  },
  "usage": {
    "useWhen": ["Adding a public route that belongs to the current portfolio."],
    "avoidWhen": ["Applying this shell to the separate local-only admin dashboard."]
  }
}
```

## 4. Navigation bar

Desktop navigation is a single horizontal row. The RS mark is a circular, thinly outlined monogram whose border uses the current route accent. The active item and hover item share a short 2px underline at the bottom of the header. The header keeps a fine bottom rule while scrolling; after scrollY exceeds 12px, it changes to an opaque tokenized navigation surface with a faint shadow. No persistent backdrop blur is applied.

At 680px and below, primary links are replaced with a menu toggle and a vertically stacked navigation panel. The mobile panel uses large type and fine row rules, traps keyboard focus while open, closes on Escape or route change, and blocks page scrolling.

```json
{
  "component": "Navbar",
  "purpose": "Keep route navigation persistent while reflecting the current section accent.",
  "sourceFiles": ["client/src/components/Navigation.tsx", "client/src/components/Navigation.module.css", "client/src/styles/editorial.css", "client/src/styles/globals.css"],
  "sourceConfidence": "confirmed",
  "anatomy": ["RS circular brand mark", "profile name", "desktop primary links", "mobile menu toggle and panel"],
  "style": {
    "desktopHeight": "4.5rem min-height",
    "mobileHeight": "4rem min-height",
    "container": "Centered .container header-inner",
    "brandMark": "2.15rem circle, 1px border in --nav-accent; Satoshi 0.68rem / 700; no decorative slash in final editorial layer",
    "linkType": "Satoshi 0.82rem / 500, --nav-label at rest",
    "desktopGap": "clamp(1.25rem, 2.4vw, 2.25rem)",
    "activeUnderline": "2px route-accent rule, anchored 0.55rem above the bottom edge",
    "surface": "Transparent before scroll; --nav-surface after scroll"
  },
  "states": {
    "default": {"bottomRule": "1px solid var(--line)", "background": "transparent"},
    "hover": {"color": "var(--nav-accent)", "transform": "translateY(-1px)", "underline": "expands from left"},
    "active": {"color": "var(--nav-accent)", "underline": "visible"},
    "focus": {"globalOutline": "2px solid var(--focus), offset 4px"},
    "scrolled": {"threshold": "window.scrollY > 12", "background": "var(--nav-surface)", "shadow": "0 0.55rem 1.5rem at 5% ink"}
  },
  "responsive": {
    "breakpoint": "680px",
    "desktop": "Wordmark plus one-line nav; Contact uses the same link treatment.",
    "mobile": "Desktop links hidden; name hidden but RS mark retained; menu opens a large type ruled panel. Odd/even links use an alternating inset."
  },
  "usage": {
    "useWhen": ["Global public-site navigation."],
    "avoidWhen": ["Turning the Contact link into a filled primary button or applying separate route-specific header structures."]
  }
}
```

## 5. Headers and page introductions

There is no single identical intro block. Most index pages use an uppercase kicker, very large sans title, and a supporting paragraph aligned in a neighboring column. The exact title size, accent, and arrangement vary by route. About is prose-led and skips the index-page side paragraph. Home uses a hero role line instead of a page kicker. Detail pages add a top back-link/date line, then a title, detail kicker, lede, and media.

```json
{
  "component": "PageIntroduction",
  "purpose": "Establish route identity with a kicker, large heading, and optional supporting copy or image.",
  "sourceFiles": ["client/src/components/Home.tsx", "client/src/components/Work.tsx", "client/src/components/Projects.tsx", "client/src/components/Photography.tsx", "client/src/components/About.tsx", "client/src/components/Food.tsx", "client/src/components/Contact.tsx", "client/src/styles/editorial.css", "client/src/components/About.module.css"],
  "sourceConfidence": "confirmed",
  "variants": {
    "homeHero": {"structure": "Role line; very large H1 with accent-colored emphasis; intro; arrow CTA; Polaroid portrait; discipline index below.", "title": "Satoshi, weight 500, clamp(4.25rem, 8vw, 8.5rem), line-height 0.88, max-width 12ch.", "layout": "Two-column opening; viewport-aware min-height; route index spans both columns."},
    "workIndex": {"structure": "Professional experience kicker and Work title; optional Polaroid at right; no standard lede paragraph.", "title": "Satoshi, route blue, clamp(5rem, 11vw, 11rem).", "layout": "Title left; optional image right; compact opening when image is absent."},
    "projectsIndex": {"structure": "Passion & kicker, Projects title, short supporting paragraph at right.", "title": "Satoshi, clamp(5.5rem, 13vw, 13rem), weight 400.", "layout": "Asymmetric two columns; supporting copy sits bottom-right."},
    "photographyIndex": {"structure": "Through my eyes kicker, Photography title, short description to the right; strong rule below.", "title": "Satoshi, clamp(4.4rem, 10vw, 10rem).", "layout": "1.35fr / 0.65fr; aligns to the bottom edge."},
    "about": {"structure": "About kicker and prose-led title; portrait with caption beside editorial paragraphs.", "title": "Satoshi, clamp(4rem, 8.5vw, 9rem), line-height 0.9.", "layout": "Spacious title section followed by portrait/text split; collapses at 900px."},
    "foodIndex": {"structure": "Kicker, two-part Food title, lede at right; separate From the kitchen intro row.", "title": "Satoshi, clamp(4rem, 8vw, 8.5rem).", "layout": "Asymmetric opening then a ruled small-label/large-serif-copy row."},
    "contactIndex": {"structure": "Contact kicker and large CTA-like heading with right-side support only where present.", "title": "Satoshi, clamp(4rem, 8.5vw, 9rem), max-width 10ch.", "layout": "Asymmetric desktop opening; stacks on mobile."},
    "detail": {"structure": "Back link and date/meta topline; detail kicker; H1; lede; adjacent hero media.", "title": "Satoshi, clamp(3.7rem, 7vw, 7.5rem), line-height 0.92; max-width 13ch.", "layout": "Two columns on desktop; one column by 680px."},
    "photoCollection": {"structure": "Back link and location/year line; location/year kicker; collection title and description; place/date/frame facts.", "title": "Newsreader or per-collection display font, clamp(4rem, 9vw, 9rem).", "layout": "Collection title and compact facts block; Photography theme may change type and framing."}
  },
  "spacing": {"introVertical": "Most index intros use clamp(6rem, 11vw, 11rem) top and clamp(4rem, 8vw, 8rem) bottom.", "titleToLede": "Typically 0.65rem–1.5rem, depending on route."},
  "responsive": {"mobile": "Intro grids become block or one column; page titles use route-specific smaller clamp ranges."},
  "usage": {
    "useWhen": ["A new route needs a recognizable editorial opening with a clear route accent."],
    "avoidWhen": ["Forcing the Home hero, About prose opening, or Photography collection detail into the same generic header."]
  }
}
```

## 6. Section headers

The recurring index-section header is a small route-colored section kicker above a large title, with an optional ArrowLink aligned to the right on desktop. The title may mix Satoshi and italic Newsreader words. Not every content section uses this pattern: gallery headings may use a divider and item count, while Work credentials are section labels over simple ruled data.

```json
{
  "component": "SectionHeader",
  "purpose": "Introduce a major content section and optionally place a route link at its far edge.",
  "sourceFiles": ["client/src/components/Home.tsx", "client/src/styles/editorial.css", "client/src/components/Photography.module.css", "client/src/components/ProjectDetail.module.css"],
  "sourceConfidence": "confirmed",
  "anatomy": ["route-colored section kicker", "large section title", "optional ArrowLink or count"],
  "layout": {"primary": "Title and kicker stack left; optional CTA aligns right and to the title baseline.", "galleryVariant": "Heading and small count share a bottom-aligned row above a fine rule."},
  "typography": {"kicker": "Satoshi 0.72rem, 600, uppercase, 0.105em tracking.", "title": "Satoshi clamp(3.2rem, 6.5vw, 6.8rem); Newsreader may be used for the emphasized phrase.", "count": "0.72rem secondary sans."},
  "spacing": {"titleOffset": "0.75rem top margin.", "headerToContent": "Usually clamp(3rem, 6vw, 6rem) for Home sections; galleries use approximately 1.5rem–3rem."},
  "responsive": {"mobile": "CTA moves below the title; align section header to start; title clamp reduces to 3rem–4.5rem."},
  "usage": {
    "useWhen": ["A major Home or index-page section has a meaningful title and optional route-level CTA."],
    "avoidWhen": ["Adding a kicker/title block to every small data subsection."]
  }
}
```

## 7. Buttons and interactive controls

Most calls to action are links with a fine underline and arrow. Filled buttons are uncommon and primarily used for form submission or navigation recovery. The cooking-mode control is a separate tactile utility. Avoid inventing primary/secondary button tiers: the current site uses a few contextual families.

```json
{
  "component": "InteractiveControls",
  "purpose": "Make navigation and actions visible with underlines, arrows, or a small number of solid surfaces.",
  "sourceFiles": ["client/src/components/common.tsx", "client/src/components/Contact.tsx", "client/src/components/ProjectDetail.tsx", "client/src/components/PhotographyCollection.tsx", "client/src/components/RecipeDetail.tsx", "client/src/components/ThemeSelector.tsx", "client/src/components/SwipeCardLink.tsx", "client/src/components/SwipeCardLink.module.css", "client/src/styles/globals.css", "client/src/styles/editorial.css", "client/src/components/ProjectDetail.module.css"],
  "sourceConfidence": "confirmed",
  "variants": {
    "arrowLink": {"style": "Inline-flex text and arrow; thin bottom rule; Satoshi 0.78rem / 600.", "hover": "Gap grows from 0.75rem to 0.9rem; rises 2px; arrow moves 4px right; color may resolve to route accent."},
    "textLink": {"style": "Underlined text, usually paired with an external or directional icon; same restrained weight.", "hover": "Shares arrow/text-link gap, lift, and icon movement."},
    "submitButton": {"style": "Square corners; 1px border; ink fill and paper text; minimum height 3.25rem; padding 0.8rem 1.2rem; no final hard shadow.", "hover": "Usually shifts to blue fill; Contact uses transparent fill with gold text."},
    "mobileMenuToggle": {"style": "Transparent, borderless 2.75rem minimum hit area; two 1px lines become a crossed close mark.", "state": "aria-expanded reflects the panel; open panel traps focus."},
    "themeChoice": {"style": "Three compact buttons inside a 1px ruled group; current preference gets a light text-color fill.", "state": "aria-pressed indicates System, Light, or Dark."},
    "galleryControls": {"style": "Simple square, outlined arrow buttons; no filled pill.", "disabled": "Disabled pagination controls retain outline and reduce opacity to 0.35."},
    "cookingMode": {"style": "Small uppercase utility with outline, circular dot, and mustard hard shadow.", "hover": "Lifts 2px and shadow shifts to copper; active presses down.", "selected": "Dark ink fill and light text while cooking mode is active."},
    "clearFilters": {"style": "Text-only accent button with underline; no container."},
    "mobileCardSwipe": {"style": "At 680px and below, a linked preview reveals a colored underlay and arrow as its top layer moves left.", "behavior": "Only deliberate horizontal left swipes act; vertical scrolling remains native. A 56px reveal completes navigation after 170ms; maximum reveal is 72px."}
  },
  "states": {
    "focus": "Global 2px focus outline with 4px offset; archive controls use a 3px route-accent outline with 2px offset.",
    "active": "Arrow links slightly lift on hover; submit and cooking mode have explicit pressed transforms. Most other controls rely on native pressed behavior.",
    "disabled": "Submit action changes its label while sending and has disabled semantics; gallery pagination uses opacity 0.35; theme/control styles do not define a broad disabled system."
  },
  "usage": {
    "useWhen": ["An action is navigational: use ArrowLink or TextLink.", "An action submits a form: use the solid SubmitButton family.", "A local state toggle already has a specific control, such as cooking mode or filters."],
    "avoidWhen": ["Creating a generic filled primary/secondary hierarchy or rounding every control."]
  }
}
```

## 8. Links

Base anchors inherit text color with no browser underline. Visible underlines are intentional: ArrowLink and TextLink use a bottom border, email is a large ruled contact link, and parent Work context uses a route-colored rule. External destinations show an external-link glyph. Project repository/live links remain visually ordinary links; a separate hard-shadow notice explains a private destination. No custom visited-link palette is declared.

```json
{
  "component": "LinkPatterns",
  "purpose": "Distinguish route navigation, inline actions, and external destinations through underlines and small directional icons.",
  "sourceFiles": ["client/src/styles/globals.css", "client/src/styles/editorial.css", "client/src/components/common.tsx", "client/src/components/Work.tsx", "client/src/components/ProjectDetail.tsx", "client/src/components/Contact.tsx"],
  "sourceConfidence": "confirmed",
  "variants": {
    "navigation": "Muted at rest; route accent on active/hover; animated bottom rule.",
    "arrowCta": "Thin text underline, text plus arrow, compact Satoshi semibold.",
    "inlineText": "Thin current-color underline, optional external arrow glyph.",
    "back": "Plain arrow-prefixed text in a detail topline; adopts route accent on hover/focus.",
    "contactDirect": "Email in large Newsreader with a long bottom rule; phone and social destinations as ruled text rows.",
    "projectDestination": "Repository/live links use TextLink with external icon; private-state notice follows directly below."
  },
  "states": {"hover": "Color transitions to route accent; directional icon moves right.", "focus": "Visible outline or context-specific accent; same affordance as hover.", "visited": "No custom visited selector found; link inherits its surrounding style."},
  "usage": {
    "useWhen": ["A link is navigational or leads to an explicit external destination."],
    "avoidWhen": ["Using an underlined link as a substitute for a separately meaningful status label."]
  }
}
```

## 9. Labels, metadata, chips, and badges

Most metadata is plain text or a rule-separated data row, not a pill. Kicker labels use small uppercase tracking. Project status and Featured labels are the exceptions: they look like small paper tags with a thin dark border, slight rotation, and a crisp offset shadow. A collection’s location/date context sits over the image. Media captions or labels appear only where the composition calls for them; the public media label helper prefers an explicit label, otherwise it shows an original filename only when the record opts in.

```json
{
  "component": "MetadataAndBadges",
  "purpose": "Keep supporting facts legible without turning all metadata into tags.",
  "sourceFiles": ["client/src/styles/editorial.css", "client/src/components/common.tsx", "client/src/components/ProjectCard.tsx", "client/src/components/PhotoCard.tsx", "shared/types/src/index.ts"],
  "sourceConfidence": "confirmed",
  "variants": {
    "kicker": {"type": "plain text", "style": "Satoshi 0.72rem / 600, 0.105em tracking, uppercase; route accent for section/detail labels."},
    "detailTopline": {"type": "plain text between rules", "style": "0.74rem sans, muted; contains back link and date/location."},
    "projectStatusBadge": {"type": "paper tag", "style": "Approximately 1.6rem high; 1px dark border; 3px hard shadow; 0.58rem bold uppercase; slight alternating tilt.", "variants": "Archived uses ochre, In Progress uses pale blue, Live uses Projects accent."},
    "featuredPin": {"type": "paper tag with tack image", "style": "1.6rem minimum height; 1px dark border; 3px offset shadow; 0.68rem bold uppercase; slight tilt.", "placement": "Project preview lower-right; Photography collection upper-left; project list lower-right."},
    "collectionContext": {"type": "image-overlay tag", "style": "Location / year; collection accent blended into paper; 1px border and hard shadow; aligned bottom-right."},
    "mediaLabel": {"type": "caption text", "rule": "Explicit imageLabel first; otherwise imageName only when showImageName is true. Captions and alt text are not visible-label fallbacks."},
    "metadataRows": {"type": "ruled definition list", "examples": "Work at-a-glance, collection facts, recipe prep/cook/servings."}
  },
  "colorRules": {"routeLabels": "Use --page-accent or the route token.", "status": "Use status-specific text/surface variables.", "mediaTheme": "Photography collections may resolve their own accent and paper palette."},
  "spacing": {"kickers": "Usually 0.75rem below/above neighboring title.", "badges": "Tight padding, no pill radius."},
  "usage": {
    "useWhen": ["A fact needs scanning or a preview needs an explicit featured/status signal."],
    "avoidWhen": ["Putting every date, category, technology, or location inside a capsule."]
  }
}
```

## 10. Image and media system

### Shared frames and portraits

The shared MediaFrame is an unrounded overflow-hidden rectangle with no default border or shadow. Images cover the frame and use normalized focal coordinates. Crop zoom is clamped from 1 to 3; the default focal point is 50% / 50%, and default zoom is 1. Clickable frames add a small 1.035 image scale on hover, using a relatively slow 800ms transition. A frame’s ratio is chosen by its composition, not imposed globally.

The Home and optional Work portrait use a distinct paper-mounted Polaroid: warm off-white stock, narrow padding, hairline edge, slight rotation, deep soft shadow, and a small two-line caption. About uses the same frame with a square portrait.

```json
{
  "component": "MediaFrame",
  "purpose": "Render image content with a consistent crop/focal-point contract while leaving frame ratio to its context.",
  "sourceFiles": ["client/src/components/common.tsx", "client/src/media-position.ts", "client/src/styles/globals.css", "client/src/styles/editorial.css"],
  "sourceConfidence": "confirmed",
  "anatomy": ["rectangular overflow-hidden frame", "image or empty span"],
  "layout": {"defaultRatio": "none; caller sets aspect-ratio or dimensions", "fit": "object-fit: cover", "objectPosition": "var(--media-focal-x, 50%) var(--media-focal-y, 50%)", "cropZoom": "Normalized 1–3; transform origin follows focal coordinates."},
  "states": {"hover": "Clickable anchor/button scales image to 1.035; 800ms --ease transition.", "focus": "Interactive wrapper receives global visible focus styling."},
  "variants": {"projectVideo": "Video/iframe uses explicit aspect ratio, dark media background, thin strong border.", "containedGalleryMedia": "Some carousel and burst frames use object-fit: contain to preserve whole image."},
  "usage": {"useWhen": ["Displaying authored image media in a known composition."], "avoidWhen": ["Using the shared frame as if it prescribed one universal ratio or image border."]}
}
```

```json
{
  "component": "PolaroidFrame",
  "purpose": "Give an authored portrait or lead image a paper-mounted, captioned presentation.",
  "sourceFiles": ["client/src/components/common.tsx", "client/src/styles/editorial.css", "client/src/components/About.module.css"],
  "sourceConfidence": "confirmed",
  "anatomy": ["warm paper figure", "MediaFrame", "optional title and detail caption"],
  "layout": {"padding": "0.8rem 0.8rem 1rem", "border": "1px solid rgba(36, 36, 31, 0.16)", "surface": "var(--photo-paper)", "transform": "rotate(-0.45deg)", "shadow": "0.75rem 1rem 2.5rem rgba(36, 36, 31, 0.14)"},
  "typography": {"captionTitle": "0.68rem, 600, truncated on one line", "captionDetail": "0.68rem at 64% opacity"},
  "variants": {"homeWorkLead": "Tall portrait frame; image minimum height about 30rem.", "aboutPortrait": "Square media frame in the same stock frame."},
  "usage": {"useWhen": ["A portrait or lead photograph anchors an editorial opening."], "avoidWhen": ["Framing every image as a Polaroid."]}
}
```

### Project imagery and galleries

Home project cards use a 4:3 lead image and 16:10 secondary images. The Projects index uses a 16:9 lead image, then 4:3 row images. On detail pages, a hero media item is separate from the ordered gallery. Project gallery layout is content-configurable: scrolling carousel, proportional mosaic rows, or a paged 3-column grid. Captions are visible only when the media record resolves a public label.

The scrolling gallery centers one active frame, dims side frames, supports pointer dragging and arrow controls, loops through cloned boundaries, and advances every 5.6 seconds while not hovered or focused. Reduced motion stops autoplay and uses immediate scrolling. Mosaic widths follow each media ratio and collapse into a vertical sequence on narrow viewports.

```json
{
  "component": "ProjectMedia",
  "purpose": "Present the project cover, hero image/video, and ordered supporting media without changing each item's source.",
  "sourceFiles": ["client/src/components/ProjectCard.tsx", "client/src/components/Projects.tsx", "client/src/components/ProjectDetail.tsx", "client/src/components/ProjectMediaGallery.tsx", "client/src/components/ProjectDetail.module.css", "client/src/components/project-media-carousel.ts"],
  "sourceConfidence": "confirmed",
  "variants": {
    "homeCardLead": {"ratio": "4 / 3", "fit": "cover", "caption": "No separate card caption; title/category/summary follow below."},
    "homeCardSecondary": {"ratio": "16 / 10", "fit": "cover"},
    "indexLead": {"ratio": "16 / 9", "fit": "cover"},
    "indexRows": {"ratio": "4 / 3", "fit": "cover", "frame": "1px strong border with project-colored hard shadow outside the frame."},
    "detailHero": {"ratio": "4 / 3", "fit": "cover for image; native controls/embed for video"},
    "scrollingGallery": {"ratio": "resolved from media set; centered active slide with side preview", "interaction": "Autoplay 5.6s, pauses on hover/focus, drag, snapping, previous/next."},
    "mosaicGallery": {"layout": "Rows flex in proportion to media ratios; a single item is capped around 42rem."},
    "gridGallery": {"layout": "3 columns, 9 items per page; 2 columns at max-width 760px."}
  },
  "states": {"mediaHover": "Scale 1.035 when the containing link/button is hovered.", "carouselInactive": "Opacity 0.42 and scale 0.965; hover 0.72; active opacity 1 and scale 1.", "video": "Native controls for MP4/WebM; privacy-enhanced YouTube/Vimeo iframe embeds."},
  "responsive": {"760px": "Project detail content becomes one column, mosaic rows stack, project grid becomes two columns.", "mobile": "Project index rows stack; cover ratios become 4:3; media gallery controls remain compact."},
  "usage": {"useWhen": ["A project has ordered image or supported video media."], "avoidWhen": ["Combining the Project list row and Home feature card into one layout; they have different hierarchy and ratios."]}
}
```

### Photography collections and photo galleries

A collection cover chooses its explicit frame ratio (landscape 4:3, portrait 4:5, wide 16:9); otherwise it uses stored dimensions and falls back to 3:2. A collection’s theme controls display/body/metadata fonts, light/dark surface/accent/border/text, heading style, and one of clean, archival, double, or borderless frames. A per-photo show-border choice can suppress the frame in gallery, burst, and collection-cover contexts.

The archive lead is separate from the collage archive. The archive uses a configurable desktop column count; each collection card has an image, location/year overlay, title, description, and photo count. Detail galleries preserve three distinct arrangements: masonry uses justified flex rows sized from image ratio; contact sheet uses a regular grid; sequence uses alternating wide, single-column compositions. A burst is an ordered interactive stack whose reserved frame matches its tallest member; layers are offset and tilted, but their images are contained without crop zoom. Clicking a photo opens a lightbox with caption, count, optional original download, arrow-key navigation, Escape close, focus trap, and focus return.

```json
{
  "component": "PhotographyCollectionMedia",
  "purpose": "Use collection-specific art direction while preserving the source image and its crop controls.",
  "sourceFiles": ["client/src/components/PhotoCard.tsx", "client/src/components/PhotoCard.module.css", "client/src/components/Photography.tsx", "client/src/components/Photography.module.css", "client/src/components/PhotographyCollection.tsx", "client/src/components/PhotographyCollection.module.css", "shared/types/src/index.ts"],
  "sourceConfidence": "confirmed",
  "variants": {
    "collectionCover": {"ratio": "4:3 landscape, 4:5 portrait, 16:9 wide; otherwise stored dimensions or 3:2 fallback", "treatment": "Theme frame border/shadow; optional border suppression; location/year paper tag."},
    "archiveLead": {"layout": "Featured collection occupies the lead position with adjacent editorial statement."},
    "archiveCollage": {"layout": "Desktop column count from build config; masonry row sizing; every item remains a collection card."},
    "masonryGallery": {"layout": "Justified rows; media flex follows frame ratio; mobile rows stack."},
    "contactSheetGallery": {"layout": "Three columns, two at max-width 900px, one at max-width 680px."},
    "sequenceGallery": {"layout": "One-column sequence at 82% width, alternating even items to the right; grows to 90% at 900px and full width on mobile."},
    "photoBurst": {"layout": "One reserved tallest-member ratio; ordered stack offset by 0.28rem x and 0.18rem y per layer, with small alternating tilt.", "imageFit": "contain; centered; crop transform disabled."},
    "lightbox": {"layout": "Dark 92% scrim; image contained within 75vh / 700px and up to 1000px width; counter and optional download below."}
  },
  "states": {"collectionCardHover": "Shadow changes to 10px 10px in the collection accent; card rises 4px / 6px while retaining its small tilt.", "burst": "Each click cycles the top frame; separate action opens the current frame.", "lightbox": "Previous/next wrap at ends; Escape closes; focus returns to trigger."},
  "responsive": {"960px": "Featured/archive geometry narrows; archive filters use two columns.", "900px": "Contact sheet changes to two columns; sequence width narrows.", "680px": "Archive and contact sheet become single-column; filters stack; sequence fills width."},
  "usage": {"useWhen": ["A photography route needs a featured collection, archive, or photo essay gallery."], "avoidWhen": ["Applying collection themes or frame treatments to unrelated project media."]}
}
```

### Video and lightbox behavior

Project videos have browser-native controls when hosted as MP4/WebM and use privacy-enhanced YouTube or Vimeo embeds for supported remote providers. The photo lightbox is a real modal, keeps background scrolling locked, uses a dark scrim, and returns focus to the item that opened it. It does not show a generic modal card surface.

```json
{
  "component": "PhotoLightbox",
  "purpose": "View a selected collection photo at large size with keyboard navigation and optional original download.",
  "sourceFiles": ["client/src/components/PhotographyCollection.tsx", "client/src/styles/globals.css", "client/src/styles/animations.css"],
  "sourceConfidence": "confirmed",
  "anatomy": ["fixed full-screen dialog", "dark scrim", "contained image", "close button", "previous/next controls", "caption and index", "optional download"],
  "layout": {"scrim": "rgba(24, 25, 22, 0.92)", "image": "object-fit: contain; height min(75vh, 700px)", "desktopWidth": "min(86vw, 1000px)"},
  "states": {"open": "280ms fade-in; body scroll locked; initial focus moves into dialog.", "keyboard": "Escape closes; Left/Right changes photo; Tab is trapped.", "close": "Focus returns to the opener.", "download": "Only shown when global and per-photo download switches and original URL are present."},
  "responsive": {"900px": "Controls move below image; image region uses 88vw."},
  "usage": {"useWhen": ["Viewing photography collection images."], "avoidWhen": ["Using this behavior as a general project gallery modal; Project galleries use carousel/grid/mosaic patterns."]}
}
```

## 11. Project cards and content previews

The Home project feature is a real card: a raised paper surface, thin edge, 6px hard shadow, image, status and optional Featured tags, category, large serif title, description, and underlined action. Cards use a 1.25fr/0.75fr feature grid, giving the first card more space. Hover/focus makes the accent shadow larger and lifts the card.

The Projects index is not a stack of those cards. It is an editorial list: a featured full-width lead preview followed by rows with a bordered/shadowed image, serif title, concise summary, and status/arrow at the far edge. A Work row is a ruled data row, not a card. Photography cards have a paper-like frame and controlled tilt; recipe previews are image-led editorial blocks with metadata rules and intentionally varied width. At 680px and below, linked previews also support a deliberate left swipe that reveals an accent-colored arrow underlay and navigates when the 56px threshold is crossed.

```json
{
  "component": "ProjectPreview",
  "purpose": "Offer two distinct project entry compositions for selection and browsing.",
  "sourceFiles": ["client/src/components/ProjectCard.tsx", "client/src/components/Projects.tsx", "client/src/styles/editorial.css", "client/src/components/ProjectCard.module.css"],
  "sourceConfidence": "confirmed",
  "variants": {
    "homeFeatureCard": {"anatomy": ["image", "status tag", "optional Featured pin", "category", "serif title", "short description", "Open project arrow"], "layout": "Two-card 1.25fr / 0.75fr grid; paper card with thin border.", "image": "First 4:3; secondary 16:10.", "shadow": "6px 6px 0 variable project backdrop; hover/focus 10px 10px route accent and translate(-4px, -6px)."},
    "projectsIndexLead": {"anatomy": ["wide image", "status tag", "optional Featured pin", "category", "serif title", "short description", "status and arrow"], "layout": "Full-width first item with 16:9 image."},
    "projectsIndexRow": {"anatomy": ["4:3 image", "category", "serif title", "short description", "status and arrow"], "layout": "Image / copy / metadata columns; fine row divider; 4rem to 4:3 image.", "hover": "Image gains 10px route-accent hard shadow and lifts; row text takes Projects accent."}
  },
  "typography": {"cardTitle": "Newsreader; first card clamp(2rem, 4vw, 4.5rem), secondary titles smaller.", "summary": "Muted sans; max-width about 34–38rem."},
  "responsive": {"680px": "Index entries stack image, copy, then status row; Home feature cards stack."},
  "usage": {"useWhen": ["Use feature card for selected Home projects.", "Use list row for the complete Projects index."], "avoidWhen": ["Rendering the Work experience list as project cards."]}
}
```

## 12. Lists and grids

The application uses layout according to content semantics:

- **Work list:** Four aligned desktop tracks: company, role, period, arrow. A shared top rule and fine row rules provide structure. Child project entries tuck below a company using a branch mark and an indented Project number. At 680px, company/role occupy the first column and period/arrow the second.
- **Projects index:** Lead item spans the list width; following items use a 3-track row. The intro copy forms a narrow sticky desktop column beside the list.
- **Photography archive:** Desktop columns are configured through build settings, not a fixed universal number; a masonry helper sets each item’s row span. Mobile is one column.
- **Work credentials:** Two equal columns for education/languages and technical focus; if only one side has content it expands to one column.
- **Project detail:** Aside plus main prose/gallery; project-specific detail uses description/technology/links in the aside and gallery in main column.
- **Contact:** Direct contact column and form column.
- **About:** Portrait and prose split.
- **Recipe index/detail:** Unequal columns, staggered previews, then a practical ingredients/method split.

```json
{
  "layoutPatterns": [
    {"layoutPattern": "WorkRows", "columns": "minmax(10rem, 1.2fr) minmax(12rem, 1fr) minmax(9rem, 0.7fr) 1.25rem", "gap": "2rem", "alignment": "Centered content and arrow at end; top and row rules.", "breakpointBehavior": "At 680px use company/role left and period/arrow right."},
    {"layoutPattern": "ProjectIndex", "columns": "0.38fr intro / 1.62fr list; list rows minmax(11rem, 0.72fr) 1.28fr auto", "gap": "clamp(3rem, 7vw, 8rem)", "alignment": "Sticky intro aligned to top; media and copy centered in rows.", "breakpointBehavior": "Intro becomes static; rows stack at 680px."},
    {"layoutPattern": "PhotographyArchive", "columns": "Configured desktop collection count; minmax(0, 1fr) per track", "gap": "clamp(1.5rem, 3vw, 2.5rem)", "alignment": "Dense grid with masonry row spans.", "breakpointBehavior": "One column at 680px."},
    {"layoutPattern": "EditorialSplit", "columns": "Unequal media/copy tracks, typically around 1fr / 0.8fr or 0.95fr / 1.35fr", "gap": "clamp(3rem, 7vw, 9rem)", "alignment": "Vertically centered or start-aligned depending on page.", "breakpointBehavior": "Stack at 900px or 680px according to composition."},
    {"layoutPattern": "DetailAsideAndProse", "columns": "Aside plus wider prose/gallery; project detail uses minmax(18rem, 0.95fr) minmax(0, 1.2fr)", "gap": "clamp(2.5rem, 5vw, 5.5rem)", "alignment": "Top-aligned; fine top rule.", "breakpointBehavior": "One column by 760px."}
  ],
  "sourceConfidence": "confirmed",
  "sourceFiles": ["client/src/styles/editorial.css", "client/src/components/Photography.module.css", "client/src/components/ProjectDetail.module.css", "client/src/components/Work.tsx", "client/src/components/Home.tsx"]
}
```

## 13. Forms and inputs

Contact is a two-column composition, not a generic form card. The form surface uses the deeper paper token, a square strong border, and internal padding. Its labels sit in ruled rows; fields are transparent and mostly defined by a bottom rule. Focus changes the bottom rule to the Contact accent and does not add a separate outline in this form. Photography archive controls are a separate outlined control panel with labeled search/select controls and a route-tinted hard shadow. Project signup is a compact bordered inline form.

Errors are plain text with alert semantics, not a red banner. Success replaces the Contact form with a small outlined check mark, heading, text, and a text action. Sending/disabled behavior is conveyed through button state and label.

```json
{
  "component": "FormControls",
  "purpose": "Collect contact, signup, or archive-filter input with visible labels and minimal field chrome.",
  "sourceFiles": ["client/src/components/Contact.tsx", "client/src/components/Contact.module.css", "client/src/components/Photography.tsx", "client/src/components/Photography.module.css", "client/src/components/ProjectDetail.tsx", "client/src/components/ProjectDetail.module.css", "client/src/styles/editorial.css"],
  "sourceConfidence": "confirmed",
  "variants": {
    "contactForm": {"layout": "Right column of Contact split; 2rem padding desktop, 1.3rem mobile; --paper-deep surface; 1px strong border.", "label": "Satoshi 0.75rem / 600; top rule; 1.25rem vertical padding.", "field": "Transparent; no side/top border; 1px strong bottom rule; 1rem text; textarea resizes vertically.", "focus": "Bottom border changes to --contact-page-accent; visible global ring is suppressed by the contact CSS."},
    "archiveFilter": {"layout": "Grid control panel with 1px strong border, raised translucent surface, 5px route-accent shadow.", "field": "Search and select use full width, 2.75rem min-height, square corners, 1px strong border.", "focus": "3px accent-mixed outline with 2px offset."},
    "projectSignup": {"layout": "Inline bordered surface, up to min(30rem, 80vw), 1.5rem padding.", "field": "Transparent underlined inputs.", "feedback": "Error or success text uses page accent."}
  },
  "states": {
    "error": {"contact": "Plain burgundy text with role=alert; form stays available."},
    "success": {"contact": "Form is replaced by check mark, serif heading, explanatory text, and Send another note action."},
    "sending": {"contact": "Button label changes to Sending… and is disabled."},
    "placeholder": "Muted placeholder text; labels remain visible above fields."
  },
  "spacing": {"contactRows": "1.25rem vertical label padding", "labelToField": "0.65rem", "formHeadingBottom": "2.5rem"},
  "usage": {"useWhen": ["Direct communication, lightweight collection filters, or a project signup."], "avoidWhen": ["Adding a large rounded card or hiding labels in placeholders."]}
}
```

## 14. Footer

The footer is the site’s stable dark closing surface. When Contact is visible it begins with a “Keep in touch” kicker, large Newsreader “Let’s Talk!” heading, and light ArrowLink. A fine border separates that from a compact metadata row with copyright, configured social links, theme selector, location, and back-to-top control. Social icons are square outlined controls and use a small hard-shadow lift on hover/focus. On mobile, the footer items stack and center, with socials and theme control placed before copyright.

```json
{
  "component": "Footer",
  "purpose": "Close the page with a conversational contact route and compact site metadata.",
  "sourceFiles": ["client/src/components/Footer.tsx", "client/src/components/Footer.module.css", "client/src/components/ThemeSelector.tsx", "client/src/styles/editorial.css"],
  "sourceConfidence": "confirmed",
  "anatomy": ["optional contact CTA row", "copyright", "configured social icons", "theme selector", "location", "back-to-top icon"],
  "layout": {"surface": "var(--footer-surface)", "topRow": "Large heading and ArrowLink across container; thin lower border.", "bottomRow": "Desktop grid: copyright, flexible space, socials/theme, location/back-to-top."},
  "typography": {"kicker": "0.72rem uppercase sans.", "heading": "Newsreader clamp(2.5rem, 4.5vw, 4.5rem).", "metadata": "0.72rem muted."},
  "states": {"socialHoverFocus": "Light fill, dark text, translate(-2px,-2px), 4px light soft shadow.", "themeSelected": "Light footer-text fill and dark footer background text."},
  "responsive": {"680px": "Bottom row becomes centered vertical stack; social, theme, copyright, and location/back-to-top are explicitly ordered."},
  "usage": {"useWhen": ["The shared public route shell."], "avoidWhen": ["Turning the footer into a bright route-colored section or duplicating the primary navigation."]}
}
```

## 15. Dividers, borders, shadows, and framing

Fine rules organize the page more often than filled panels. Standard rows use `--line`; key section starts and ends use `--line-strong`. The header keeps its own bottom rule. Contact and collection filter panels have stronger outlines. Project and Photography cards use hard-edged offset shadows as local expressive signals. The Polaroid uses a soft broad shadow. Most detail media and gallery images have no outer shadow. Corners remain square except for explicit circles.

```json
{
  "component": "SeparatorsAndFraming",
  "purpose": "Use fine rules and selective frames to create hierarchy without defaulting to elevated panels.",
  "sourceFiles": ["client/src/styles/tokens.css", "client/src/styles/editorial.css", "client/src/components/Photography.module.css", "client/src/components/PhotoCard.module.css"],
  "sourceConfidence": "confirmed",
  "variants": {
    "fineRule": "1px solid var(--line); between data rows, footer content, and list entries.",
    "strongRule": "1px solid var(--line-strong); section starts, page-intro bottoms, contact split, credentials, and media headings.",
    "outlinedPanel": "1px solid var(--line-strong); square; Contact form and Photography archive filters.",
    "offsetShadow": "Hard-edged 3px–6px offsets for status tags and cards; may grow to 10px on hover.",
    "paperFrame": "Thin edge, warm frame surface, slight tilt, broad soft shadow for portrait Polaroid.",
    "mediaFrame": "Usually square-edged, no border/shadow; explicit project/photo theme exceptions.",
    "photoThemeFrame": "Per-collection clean (1px), archival (0.45rem paper + soft offset), double (4px double), or borderless."
  },
  "usage": {"useWhen": ["A line clarifies hierarchy or an authored preview needs a distinct paper edge."], "avoidWhen": ["Using shadows on every block or rounding all image and control edges."]}
}
```

## 16. Interaction and motion

Motion is short and attached to affordance. Navigation underlines reveal from left; links open their gap and move their arrow; project/collection cards shift against hard shadows; images use a gentle slow zoom. There is a restrained route/view transition. The site globally honors reduced motion, removing or near-zeroing CSS transitions and animations; the project carousel also stops autoplay.

```json
{
  "motion": {
    "sourceConfidence": "confirmed",
    "sourceFiles": ["client/src/styles/animations.css", "client/src/styles/editorial.css", "client/src/styles/globals.css", "client/src/components/ProjectMediaGallery.tsx", "client/src/components/SwipeCardLink.tsx", "client/src/components/SwipeCardLink.module.css"],
    "fast": "160ms–220ms for link, button, and underline feedback",
    "standard": "220ms–360ms for header/card surface changes",
    "image": "800ms --ease for MediaFrame zoom",
    "easing": {"--ease": "cubic-bezier(0.22, 0.61, 0.36, 1)", "--ease-out": "cubic-bezier(0.16, 1, 0.3, 1)"},
    "patterns": {
      "navUnderline": "Opacity plus scaleX; expands from left on hover/active.",
      "arrowLink": "Gap and color transition, 2px upward nudge, icon moves 4px right.",
      "card": "Selected project/collection cards rise 4px/6px while hard shadow grows.",
      "route": "Fallback route frame 360ms; browser view transition uses 180ms old / 520ms new.",
      "lightbox": "280ms opacity entrance.",
      "carousel": "500ms slide opacity/scale; 5.6s autoplay interval while idle.",
      "mobileCardSwipe": "Top card layer moves left to reveal a route-colored arrow; 190ms easing; navigation completes at -56px and caps at -72px."
    },
    "reducedMotion": "Global prefers-reduced-motion reduces transition/animation duration to 0.001ms and disables route/hero entrance; project carousel disables autoplay and smooth scrolling."
  }
}
```

## 17. Responsive system

The application has a few meaningful breakpoints rather than one perfectly uniform grid system. 960px and 900px are both used for different compositions; 760px belongs to the project detail media system; 680px is the main mobile boundary for global navigation and page stacking. Keep the existing content order when collapsing. Some behaviors are explicit: desktop Photography archive columns come from build configuration, while the mobile archive is always one column.

```json
{
  "component": "ResponsiveSystem",
  "purpose": "Describe the actual breakpoints and how each content composition changes.",
  "sourceFiles": ["client/src/styles/globals.css", "client/src/styles/editorial.css", "client/src/components/Photography.module.css", "client/src/components/PhotographyCollection.module.css", "client/src/components/ProjectDetail.module.css", "client/src/components/About.module.css", "client/src/components/Work.module.css"],
  "sourceConfidence": "confirmed",
  "breakpoints": {
    "960px": ["Photography lead/filters and Home/project feature layout compress; collection sequence narrows."],
    "900px": ["About portrait/prose split stacks; Photography contact sheet becomes two columns; collection header and lightbox controls reflow."],
    "760px": ["Project detail aside/prose becomes one column; mosaic rows stack; project media grid becomes two columns."],
    "680px": ["Primary nav becomes mobile menu; header height 4rem; brand name hides; body type is 15px; gutters 1.25rem; most editorial columns stack."]
  },
  "mobileBehavior": {
    "home": "Hero stacks; portrait follows copy; discipline index becomes two columns.",
    "work": "Header and optional portrait stack; Work row uses two tracks while retaining company/role and period/arrow relationships.",
    "projects": "Index row stacks image, copy, status; feature cards stack; row media becomes 4:3.",
    "photography": "Archive and contact sheet become one column; filters stack; collection detail sequence fills available width.",
    "contact": "Direct links precede the full-width form; form padding narrows.",
    "about": "Portrait and prose stack in source order.",
    "footer": "Rows stack and center; social/theme controls remain usable at full touch size."
  },
  "usage": {"rule": "Preserve reading order and each content type’s relationship while collapsing; do not simply shrink desktop columns."}
}
```

## 18. Composite patterns

These are useful starting points when adding a page that should feel related to this portfolio. They are compositions already present in source, not new component prescriptions.

```json
{
  "pattern": "HomeEditorialSpread",
  "composedOf": ["RoleLine", "DisplayHeading", "IntroCopy", "ArrowLink", "PolaroidFrame", "DisciplineIndex"],
  "sourceFiles": ["client/src/components/Home.tsx", "client/src/styles/editorial.css"],
  "sourceConfidence": "confirmed",
  "layout": "Two-column viewport-aware opening; copy left, tall paper-framed portrait right; discipline index is a ruled row below.",
  "usage": "Use for an authored personal landing page with one primary portrait and several site disciplines."
}
```

```json
{
  "pattern": "WorkExperienceList",
  "composedOf": ["WorkCompany", "WorkRole", "WorkPeriod", "RowArrow"],
  "sourceFiles": ["client/src/components/Work.tsx", "client/src/styles/editorial.css", "client/src/content-presentation.ts"],
  "sourceConfidence": "confirmed",
  "layout": "Desktop four-track ruled list; subentries indent with branch glyph and Project number; mobile aligns role/company left and time/arrow right.",
  "usage": "Use for chronological professional experience where parent/child hierarchy matters; do not turn entries into cards."
}
```

```json
{
  "pattern": "ProjectIndexRow",
  "composedOf": ["MediaFrame", "ProjectStatusBadge", "FeaturedPin", "ProjectCategory", "SerifTitle", "Summary", "StatusAndArrow"],
  "sourceFiles": ["client/src/components/Projects.tsx", "client/src/components/ProjectCard.tsx", "client/src/styles/editorial.css"],
  "sourceConfidence": "confirmed",
  "layout": "Featured item is a wide lead; remaining items use image/copy/status tracks and fine row rules.",
  "usage": "Use for scanning a complete set of independent projects."
}
```

```json
{
  "pattern": "ProjectCaseStudy",
  "composedOf": ["DetailTopline", "DetailKicker", "DisplayHeading", "Lede", "ProjectMedia", "DescriptionBlock", "TechnologyList", "ProjectLinks", "ProjectGallery"],
  "sourceFiles": ["client/src/components/ProjectDetail.tsx", "client/src/components/ProjectMediaGallery.tsx", "client/src/components/ProjectDetail.module.css", "client/src/styles/editorial.css"],
  "sourceConfidence": "confirmed",
  "layout": "Two-column title/media hero; ruled aside/prose body; aside contains description, technologies, and external links, while main column contains the media gallery.",
  "usage": "Use for project storytelling with a meaningful media sequence and supporting metadata."
}
```

```json
{
  "pattern": "PhotographyArchiveAndEssay",
  "composedOf": ["FeaturedCollection", "EditorialStatement", "ArchiveControls", "CollectionCard", "CollectionTheme", "CollectionGallery", "PhotoBurst", "PhotoLightbox"],
  "sourceFiles": ["client/src/components/Photography.tsx", "client/src/components/PhotoCard.tsx", "client/src/components/PhotographyCollection.tsx", "client/src/components/Photography.module.css", "client/src/components/PhotographyCollection.module.css"],
  "sourceConfidence": "confirmed",
  "layout": "One featured lead plus grouped collection archive; collection detail carries its own palette, type, image frame, and gallery layout.",
  "usage": "Use for photograph collections and visual essays; keep individual collection art direction scoped to that collection."
}
```

```json
{
  "pattern": "ContactSplit",
  "composedOf": ["ContactHeading", "DirectLinks", "Location", "RuledContactForm", "SubmitButton", "InlineFeedback"],
  "sourceFiles": ["client/src/components/Contact.tsx", "client/src/components/Contact.module.css", "client/src/styles/editorial.css"],
  "sourceConfidence": "confirmed",
  "layout": "Large page intro followed by a rule and a 0.7fr / 1.3fr direct-contact/form split; stacks on mobile.",
  "usage": "Use when direct contact methods and a short form should be equally discoverable."
}
```

```json
{
  "pattern": "RecipeNotebook",
  "composedOf": ["FoodPageIntroduction", "RecipeCard", "RecipeMetadata", "RecipeDetailHero", "CookingMode", "Ingredients", "NumberedMethod", "OptionalPhotoSequence"],
  "sourceFiles": ["client/src/components/Food.tsx", "client/src/components/RecipeCard.tsx", "client/src/components/RecipeDetail.tsx", "client/src/components/RecipeDetail.module.css", "client/src/styles/editorial.css"],
  "sourceConfidence": "confirmed",
  "layout": "Unequal editorial cards and a practical recipe detail; ingredients and method split on desktop, with cooking mode removing introductory prose and story/notes.",
  "usage": "Use for authored recipe content; retain scan-friendly measurements, ruled ingredients, and numbered method steps."
}
```

## 19. Usage rules

### Do

- Start with the neutral paper surface and charcoal text; use the route accent for kickers, active navigation, and selected interactive emphasis.
- Use Satoshi for ordinary headings and UI text. Reach for Newsreader when the composition already uses an editorial title, caption, or prose moment.
- Choose one composition that fits the content: ruled list, split editorial block, raised preview, or image sequence.
- Give images a deliberate ratio and preserve focal coordinates and zoom when the source supports them.
- Use fine rules to organize rows and information; reserve hard shadows for authored preview tags/cards.
- Keep visible labels explicit. Filename labels are opt-in.
- Preserve responsive reading order and keyboard-visible focus.

### Avoid

- A repeated grid of identical rounded cards.
- Converting every kicker, date, technology, status, or category into a chip.
- Full-page saturated route colors, uniform card elevation, or shadow on every media frame.
- Forcing the Home hero, Work history, Project index, and Photography archive into one shared content layout.
- Using the main token named `--mono` as evidence that the shared font is monospaced; its current value aliases Satoshi.
- Adding motion to content that does not use motion or defeating reduced-motion settings.

### Maintain consistency in

- The 1320px centered container and fluid gutters.
- Neutral theme foundation, fine rule language, square controls, and restrained route color.
- Persistent sticky navigation, route-colored active state, and common dark footer.
- Page-heading voice, accessible focus visibility, and reduced-motion behavior.
- Media focal/zoom behavior and explicit label rules.

### Allow variation in

- Route accent and softly tinted surface.
- Hero title size, page introduction geometry, and support-copy placement.
- Project feature-card versus project-index row treatment.
- Collection-specific typography, palette, photo border, and gallery arrangement.
- Media ratio, focal point, crop zoom, and whether a frame is borderless or archival.
- Content density: spacious Home/Photography, compact Work rows, detailed Project/Recipe bodies.

## Practical source map

| Pattern | Start with |
| --- | --- |
| Tokens and shared shell | `client/src/styles/tokens.css`, `client/src/styles/globals.css`, `client/src/styles/editorial.css` |
| Navigation/footer | `client/src/components/Navigation.tsx`, `client/src/components/Footer.tsx` |
| Shared links, frames, and icons | `client/src/components/common.tsx` |
| Home and project previews | `client/src/components/Home.tsx`, `client/src/components/ProjectCard.tsx` |
| Work index/detail | `client/src/components/Work.tsx` |
| Projects index/detail/media | `client/src/components/Projects.tsx`, `client/src/components/ProjectDetail.tsx`, `client/src/components/ProjectMediaGallery.tsx` |
| Photography archive/detail | `client/src/components/Photography.tsx`, `client/src/components/PhotographyCollection.tsx`, `client/src/components/PhotoCard.tsx` |
| About | `client/src/components/About.tsx`, `client/src/components/About.module.css` |
| Food/recipes | `client/src/components/Food.tsx`, `client/src/components/RecipeDetail.tsx` |
| Contact/form | `client/src/components/Contact.tsx`, `client/src/components/Contact.module.css` |

