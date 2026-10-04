# Devpost submission (copy and paste)

**Project name:** ClaimScout

**Tagline:** An AI agent that finds money you're actually owed.

**Track:** Best Apps and Agents

## Inspiration
Most people who qualify for a class action settlement never file; an FTC study found a median claims rate of about 9% in consumer class actions. The money exists and people qualify, but the deadlines are scattered across hundreds of settlement sites written in legal language, and nobody has time to read them. We wanted an agent that does the reading for you and is honest about whether you actually qualify.

## What it does
You tell ClaimScout what you've bought, the stores and services you use, and any data breach letters you've received. It searches the live web for open settlements, reads each one, pulls out the payout, deadline and proof needed, and decides whether you're likely, maybe or unlikely to be in the class. Every match says exactly what to confirm before filing. One click puts every deadline in your calendar with a three-day reminder. It also points you to the official free unclaimed-property search.

## How we built it
- **NVIDIA Nemotron on Nebius Token Factory** powers every AI step through the OpenAI-compatible API. ClaimScout discovers available Nemotron models at startup and assigns them by job: a fast Nemotron model plans searches and extracts structured data from pages (high volume, low latency), and the largest Nemotron reasoning model makes the eligibility decision, where accuracy matters most.
- **Tavily** searches the live web and extracts full page text from the most relevant settlement pages.
- A four-stage pipeline: plan → research → extract → judge. Pages are processed in parallel, expired settlements are dropped, and duplicates across sources are merged.
- **Streamlit** for the interface, with a demo mode that works without API keys.
- A pytest suite covers the full pipeline with faked model and search clients.

## Challenges we ran into
- Settlement pages are messy and inconsistent. We had the model leave fields blank rather than guess, and dropped anything past its deadline.
- Eligibility is a legal claim, so false positives are harmful. The judge prompt only reasons from facts the user stated, and we hide "unlikely" results instead of padding the list.
- Model IDs change as NVIDIA releases new Nemotron versions, so we discover them at runtime instead of hard-coding them.

## Accomplishments that we're proud of
An agent whose job is to say "no" when the honest answer is no, while still finding real money for people.

## What we learned
Splitting work between a fast model and a reasoning model made the agent both quicker and more accurate than using one model for everything.

## What's next
Saved profiles with weekly alerts for new matching settlements, guided claim-form filling with the user reviewing every field, and direct state unclaimed-property lookups.

## Built with
nvidia-nemotron, nebius-token-factory, tavily, python, streamlit, pydantic

---
**Feedback on Nebius / NVIDIA tools:** write this yourself after you run it with real keys: what was easy, what was confusing, what broke. Honest, specific feedback is what wins the "Most Valuable Feedback" prizes ($100 cash, 10 winners).
