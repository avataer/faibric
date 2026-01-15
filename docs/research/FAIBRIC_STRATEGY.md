# Faibric Strategic Document

**Last Updated:** January 8, 2026
**Status:** Active Strategy

---

## 1. WHAT IS FAIBRIC

Faibric is an AI-powered app builder that competes with Lovable, v0, Base44, and Bolt. Unlike competitors who chase volume with low-ARPU customers, Faibric targets the profitable middle ground.

**Core Value Proposition:**
Turn ideas into deployed web apps in minutes, not months. Full-stack (frontend + backend + database + auth + hosting) from natural language.

**Tech Stack:**
- Frontend: React 18 + TypeScript + Vite
- Backend: Django 5.0 + DRF + Celery
- AI: Claude Opus 4.5 (claude-opus-4-5-20251101)
- Database: PostgreSQL + Redis
- Hosting: Render.com (current), DigitalOcean (planned)

---

## 2. PRODUCT DECISIONS (NON-NEGOTIABLE)

These are foundational choices that inform all other decisions. They are final.

### Decision 1: No Direct B2B Sales. Ever.

**Rule:** No sales teams. No personal sales from one physical person to another. Only scalable solutions.

**Allowed:**
- AI-powered chatbots for sales conversations
- AI-generated email outreach campaigns
- AI-driven LinkedIn outreach (automated)
- Self-serve signup and payment
- Content marketing and SEO
- Paid ads (Google, Meta, etc.)

**Forbidden:**
- Hiring salespeople
- Personal demos (human-to-human)
- Enterprise sales cycles
- Account executives
- Sales calls

**Rationale:** Sales teams don't scale. Every dollar of revenue should come from systems, not people. If it requires a human to close, it's not a Faibric customer.

---

### Decision 2: Virality & Network Effects Are Core

**Rule:** The product must be inherently viral. Network effects must be built into the core, not bolted on.

**Viral mechanics (required in product):**
- "Built with Faibric" badge on all free-tier apps (every app is an ad)
- Share template → referrer gets credits
- Invite collaborator → both get credits
- Public template gallery (users see what others built)
- Social proof: "10,000 apps built this week"

**Network effects (required in product):**
- Templates improve with usage data (more users = better matching)
- User-generated templates (marketplace potential)
- Community features (comments, ratings, forks)

**Test:** If removing the viral mechanic doesn't hurt growth projections, it's not viral enough.

---

### Decision 3: Freemium with Consumables (Profitable from Day 1)

**Rule:** No big price shown upfront. But EVERY interaction must be profitable (or very close to it).

**Core principle:** Customer pays upfront → then gets value. Never the reverse.

**Pricing structure:**
| Action | User Pays | Our Cost | Profitable? |
|--------|-----------|----------|-------------|
| Sign up | $0 | ~$0 | Neutral |
| Generate app (template) | $0 | ~$0 | Neutral |
| Deploy app | Hosting fee | <Hosting fee | YES |
| Request change | Credit fee | <Credit fee | YES |
| Add custom domain | Domain fee | <Domain fee | YES |

**Forbidden:**
- Free trials that cost us money
- "First month free" promotions
- Loss-leader pricing
- Subsidizing users hoping they convert later

**Allowed small exception:** Minimal CAC budget for acquisition (e.g., $1-2 per signup in ad spend), but post-signup every action must be profitable or neutral.

**The VONS psychology:** Price LOOKS small, but aggregates to real revenue. No one sees "$200/year" - they see "$5/month" and "$1/change."

---

### Decision 4: Monthly Stripe Subscriptions Only

**Rule:** All payments are monthly recurring subscriptions through Stripe. No exceptions.

**Allowed:**
- Monthly subscription for hosting (e.g., $9/month)
- Monthly subscription for change credits (e.g., $19/month for 30 credits)
- Monthly subscription tiers (Starter, Pro, Business)

**Forbidden:**
- Weekly billing
- Annual billing (no annual discounts)
- One-time purchases
- Lifetime deals
- Pay-per-use without subscription wrapper
- Any payment processor other than Stripe

**Rationale:**
1. Monthly = predictable MRR, easier to forecast
2. No annual = no large refund requests, no "I forgot I subscribed"
3. Stripe only = one integration, one dashboard, one source of truth
4. Subscriptions = recurring revenue, higher LTV than one-time

**Implementation:**
- Change credits sold as "$X/month for Y credits" subscription
- Hosting sold as "$X/month" subscription
- Even add-ons (custom domain, extra storage) are monthly subscriptions

---

## 3. BUSINESS MODEL: FREEMIUM WITH CONSUMABLES

### The McDonald's Model

Competitors burn money on AI for every user. Faibric uses AI once per template, then serves pre-generated code. Margins improve with scale.

**The Secret:** "The best AI app builder barely uses AI."

### Pricing Structure

| Component | Price | User Perception | Actual Economics |
|-----------|-------|-----------------|------------------|
| **Generation** | FREE | "Wow, free AI generation!" | Pre-generated templates, ~$0 cost |
| **Hosting** | ~$5-20/month | "Cheap enough to forget" | Break-even or small profit |
| **Changes** | $1 per credit | "Just $1 to fix this" | 70-80% margin per API call |

### Psychology: Escaping the Dead Zone

The SCRT model identifies $100-$10,000 as the "dead zone" where nothing sells. This model splits the decision:

1. **FREE generation** → No decision, just try it
2. **$5-20/month hosting** → Below evaluation threshold
3. **$1/change** → Transactional, feels like buying a song

Users end up paying $100-300/year without triggering the "is this worth it?" evaluation.

### Pricing A/B Test Plan

**Display Price Strategy (VONS Model):**
- Show $20/month as "regular price"
- Permanent "sale" → $9/month (or $5/month for basic)
- Users unlikely to check price page again after signup
- All prices are monthly subscriptions (no annual - see Decision 4)

**Change Credits (as monthly subscriptions):**
- $5/month for 10 credits
- $9/month for 25 credits
- $19/month for unlimited changes

### Unit Economics

**Average user scenario:**
| Item | Revenue | Cost | Margin |
|------|---------|------|--------|
| Hosting (12 mo) | $60-240 | $24-48 | $36-192 |
| ~80 changes/year | $80 | $20 | $60 |
| **Total** | **$140-320** | **$50-70** | **$90-250** |

**Target metrics:**
- Gross margin: 60-70%
- CAC target: <$50 (achievable with content/SEO at this price point)
- Payback: <3 months

---

## 4. PRE-GENERATION STRATEGY

### Golden Templates (30 Core)

Instead of generating fresh for each user, serve pre-built templates customized with their branding/names in <5 seconds.

**Template Categories:**

| Category | Templates | Use Cases |
|----------|-----------|-----------|
| Client Portals | 5 | Freelancer client portal, Agency client dashboard, Consultant project tracker |
| Booking Systems | 3 | Service booking, Appointment scheduler, Event registration |
| Simple CRM | 3 | Contact manager, Lead tracker, Pipeline dashboard |
| Dashboards | 5 | Sales metrics, Ops dashboard, Team performance, Analytics viewer |
| Landing + Forms | 5 | Lead capture, Waitlist, Contact form, Survey, Feedback |
| Inventory/CRUD | 3 | Product inventory, Asset tracker, Simple database UI |
| Membership | 3 | Member directory, Community portal, Subscription manager |
| Project Management | 3 | Task tracker, Kanban board, Status dashboard |

### Template Matching Flow

1. User describes app in natural language
2. NLP matches to closest template (Opus 4.5 call - cache response)
3. Auto-inject: company name, colors, logo, field names
4. Serve in <5 seconds (instant gratification)
5. User sees "Generated with Opus 4.5" (true, just pre-generated)

### Change Credit Monetization

When user requests customization:
- "Make header blue" → $1 (trivial CSS, but feels like $50 of work)
- "Add new field" → $1 (database + UI change)
- "Connect to Stripe" → $1 (integration work)
- "Change layout" → $1 (structural modification)

**Margin per change:** $1 revenue - $0.15-0.30 cost = 70-85% gross margin

---

## 5. COMPETITIVE POSITIONING

### Competitor Weaknesses

| Competitor | Weakness | Faibric Advantage |
|------------|----------|-------------------|
| **Lovable** | $200M ARR but enterprise-focused, expensive ($20-50/mo) | Cheaper entry, same output |
| **v0** | Frontend only, no backend | Full-stack from prompt |
| **Base44** | Wix acquisition = small business stigma | Independent, developer credibility |
| **Bolt** | Token consumption unpredictable, complex apps fail | Fixed pricing, pre-tested templates |

### Why We Win

1. **Speed**: Pre-generated = instant (competitors wait 30-60 seconds)
2. **Reliability**: Templates are tested, competitors generate fresh (bugs)
3. **Price**: FREE entry vs $20/month minimum
4. **Psychology**: Consumables feel less committal than subscriptions

### The Technical Middle Niche

Competitors leave the "technical middle" unserved:
- Too technical for Wix/Squarespace users
- Too simple for developers using Cursor

**Faibric attacks from both edges:**
- Lower price than Lovable → captures price-sensitive technical users
- Simpler than Cursor → captures non-devs who want code output

---

## 6. GO-TO-MARKET STRATEGY

### Phase 1: Template Library & Viral Loop (Months 1-2)

**Build:**
- 30 golden templates covering 80% of use cases
- Smart matching system (NLP → template)
- Change credit system
- "Powered by Opus 4.5" branding

**Launch:**
- ProductHunt: "Free AI app builder with Opus 4.5"
- Twitter/X: Demo videos showing instant generation
- Reddit: r/SideProject, r/startups, r/webdev

**Viral mechanics:**
- "Built with Faibric" badge on free tier apps
- Share template → referrer gets 5 free credits
- First app free forever (with badge)

### Phase 2: Content + SEO (Months 2-4)

**Target keywords (lower CPC, higher intent):**
| Keyword | Est. CPC | Strategy |
|---------|----------|----------|
| "build internal tools fast" | $3-5 | Blog + landing page |
| "retool alternative" | $4-6 | Comparison page |
| "custom dashboard software" | $3-5 | Template showcase |
| "spreadsheet to app" | $2-4 | Tutorial content |

**Content pieces:**
1. "I built 5 apps in 1 hour with AI (free)"
2. "Retool vs Faibric: Which is right for you?"
3. "From spreadsheet to app in 10 minutes"
4. "The $50K internal tool for $5/month"

### Phase 3: Paid Ads A/B Testing (Months 4-6)

**Google Ads:**
- Start with $2K/month budget
- Test: "Free AI app builder" vs "Build apps in minutes" vs "Opus 4.5 powered"
- Target: "internal tools", "admin panel builder", "dashboard software"

**Meta Ads:**
- Video demos (instant generation is visually compelling)
- Retargeting blog visitors
- Lookalike audiences from converters

### Phase 4: Scale What Works (Months 6-12)

- Double down on winning channels
- Expand template library based on demand
- Add vertical-specific templates (healthcare, real estate)
- Introduce agency/reseller tier

---

## 7. INFRASTRUCTURE ROADMAP

### Current State (MVP)
- Render.com hosting
- ~$100/month fixed costs
- Claude API at ~$0.95/generation

### Target State (Scale)
- DigitalOcean self-hosted (lower cost)
- Pre-generated templates (eliminate per-generation AI cost)
- Change credits = only AI cost
- Target: <$2/month per active user hosting cost

### Migration Plan
1. Keep Render for MVP validation
2. Once 100+ paying users, migrate to DigitalOcean
3. Shared infrastructure for templates (multi-tenant)
4. Per-user isolation only for paid custom domains

---

## 8. METRICS TO TRACK

### North Star Metrics

| Metric | Month 3 | Month 6 | Month 12 |
|--------|---------|---------|----------|
| Active Users | 1,000 | 5,000 | 25,000 |
| Paying Users | 100 | 500 | 2,500 |
| MRR | $1,000 | $5,000 | $25,000 |
| ARPU | $10/mo | $10/mo | $10/mo |

### Conversion Funnel

| Stage | Target |
|-------|--------|
| Visit → Sign up | 10% |
| Sign up → Generate app | 60% |
| Generate → Deploy | 40% |
| Deploy → First payment | 15% |
| First payment → Month 2 | 70% |

### Unit Economics Targets

| Metric | Target |
|--------|--------|
| CAC | <$30 |
| Payback | <3 months |
| Gross margin | >65% |
| Monthly churn | <8% |

---

## 9. RISKS & MITIGATIONS

| Risk | Probability | Mitigation |
|------|-------------|------------|
| Templates don't cover use cases | Medium | Start with 30, add based on demand |
| "Pre-generated" feels like bait-and-switch | Medium | Over-invest in matching UX |
| Competitors copy model | High | Execution speed, brand loyalty |
| Change credits feel nickel-and-dime | Medium | Offer unlimited tier as upsell |
| Hosting costs spike | Low | Multi-tenant, DigitalOcean migration |

---

## 10. THE SCRT MODEL ALIGNMENT

From Anton's framework:

**Flow State:** The founder is the business. All value comes from flow.

**Secret:** "The best AI app builder barely uses AI" - pre-generate templates, monetize changes.

**Dead Zone Escape:** Split pricing decisions below $100 threshold.

**25% Test:** Can we get 25% of a niche in 90 days?
- Target: "Solo founders who want internal tools"
- Size: ~100,000 people actively looking
- 25% = 25,000 users
- Achievable with viral + content strategy

**Monopoly Path:** Start with "free AI app builder" → dominate → add features → raise prices → expand to adjacent markets.

---

## 11. IMMEDIATE NEXT STEPS

### Week 1
- [ ] Build template matching system
- [ ] Create first 10 templates (most common use cases)
- [ ] Implement change credit system

### Week 2
- [ ] Add "Powered by Opus 4.5" branding
- [ ] Set up hosting billing ($5/month)
- [ ] Create landing page with demo

### Week 3
- [ ] Soft launch to 50 beta users
- [ ] Collect feedback on templates
- [ ] Iterate on matching accuracy

### Week 4
- [ ] ProductHunt launch
- [ ] Start content marketing
- [ ] Enable paid change credits

---

## SOURCES

- SCRT Model (Anton's Framework)
- Market Research: $45.5B low-code market, 31% CAGR
- Competitor Analysis: Lovable ($200M ARR), v0 (6M devs), Base44 (Wix $80M), Bolt (9M visits)
- CPC Benchmarks: $3-8 for relevant keywords
- Conversion Benchmarks: 18.5% trial-to-paid median
