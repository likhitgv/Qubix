# KAIRO: NASA Space Apps Challenge 2026 submission

Everything below is ready to paste into the submission page. Fill in the `[brackets]` only.
**Deadline: 15 November 2026, 11:59 pm local time (no exceptions).**

## Project name

KAIRO

## Challenge

Field Shift: Adapting Farms with NASA Data

## Summary (141 words; limit is 50-200)

KAIRO helps farmers in India decide what to plant next. A farmer picks a state and district, or drops a pin on the map, then answers three simple questions: soil type, how the field is irrigated, and what was grown before. KAIRO reads NASA POWER daily weather records for that location, averages past kharif and rabi seasons, and compares them with crop needs from a sourced crop database. It recommends a two-season crop plan, explains why it may fit the field, names the main trade-off, and offers two alternatives. Every score can be inspected under "How this was calculated". KAIRO covers all of India through the nearest NASA weather grid cell and was tested in five Karnataka districts. It is decision support, not agronomic advice, and always tells users to check with a local agronomist. Saved plans can be reopened later.

## NASA data used (required for global awards)

- **NASA POWER** daily point and gridded data (temperature, rainfall, humidity): 882 grid points covering India, daily 2021-2026, plus daily point data for five Karnataka districts. <https://power.larc.nasa.gov/>
- **NASA GPM IMERG Final V07B** rainfall: a January 2025 sample for four districts (used for checking rainfall, not in the recommendations).

NASA POWER is gridded, modelled data (about 56 km cells). KAIRO says so on every page; it does not present it as a field measurement.

## Use of AI tools (must be disclosed)

> This project used AI tools. Anthropic's Claude (through Claude Code) helped the team write and review code, tests and documentation and draft the interface; the team directed the work and reviewed the results. KAIRO also has an optional feature that can send KAIRO's own computed results to a hosted language model (Groq) to explain them in plain language or in Kannada or Hindi. That text is accepted only if every number in it matches KAIRO's computed data; otherwise a fixed offline summary is shown. The crop reference data and all weather data come from the cited sources, not from AI.

The same statement is shown inside the app (About page) and in the README.

## Links

- Code (public): <https://github.com/likhitgv/Qubix>
- Demo slides (7): <https://github.com/likhitgv/Qubix/blob/main/FIELDWISE_AI/docs/demo/KAIRO_Demo.pdf> (editable version: `KAIRO_Demo.pptx` in the same folder)
- Demo video (28 s, captioned, AI-use mark on every frame): <https://github.com/likhitgv/Qubix/blob/main/FIELDWISE_AI/docs/demo/KAIRO_Demo_28s.mp4>
  These GitHub links work once the demo PR is merged to `main`. For the most reliable video link, upload the MP4 to YouTube as Public or Unlisted and paste that instead.
- Before submitting: put your team name in `TEAM` at the top of `docs/demo/build_demo.py` and re-run `py -3.11 docs/demo/build_demo.py`, or edit slides 1 and 7 of the PPTX.
- Team: `[team name]`, `[member names, 1 to 6]`

## Demo: 7 slides maximum (or a video of 30 seconds or less), publicly viewable, no password

1. **Title.** KAIRO. "Crop planning from NASA weather records." Challenge name.
2. **The problem.** Weather is changing; farmers choose crops with little local weather evidence.
3. **What KAIRO does.** Four questions in, one clear recommendation out (screenshot of the Recommendation page: Best option, why it fits, keep in mind, two alternatives).
4. **NASA data.** NASA POWER daily weather, 882 grid points across India, 2021-2026 (screenshot of the coverage map).
5. **How it works.** Location -> nearest NASA grid cell -> seasonal averages -> compare with crop needs -> ranked plans; "How this was calculated" shown.
6. **Honest limits.** Tested in five Karnataka districts; six crops; some crop figures still being verified and flagged in the app; decision support only.
7. **Team, AI disclosure, links.** Team names, the AI-use statement above, GitHub link.

## 30-second video script (if you record instead of slides)

- 0-5 s: "KAIRO turns NASA weather records into a crop plan for your field."
- 5-15 s: Screen: pick Karnataka, Dharwad, choose soil, choose rainfed, press Get recommendation.
- 15-25 s: Screen: the Best option card with reasons and the Keep in mind line, then the map of NASA coverage.
- 25-30 s: "Built on NASA POWER data. Decision support: check with a local agronomist."
- Add English subtitles if you speak another language. Add the on-screen line "AI-assisted: built with Claude".

## What to say honestly if judges ask

- Only five Karnataka districts were validated; elsewhere results are a starting point.
- The crop database has six crops. Groundnut, chickpea and maize figures come from secondary sources and are flagged "needs verification" in the app.
- Chickpea's stored rainfall range is an annual figure compared with seasonal totals.
- Season windows (kharif Jun-Oct, rabi Nov-Mar) are assumptions.
- No yield, profit or water-saving claims are made.

## Final checklist

- [ ] All team members registered for the same event; 1 to 6 members
- [ ] Project name, summary (50-200 words), demo link added on the submission page
- [ ] Demo is public with no password (7 slides or 30 s video)
- [ ] AI-use statement included
- [ ] Repository is public (it is) and the latest code is on `main`
- [ ] Use the lock toggle on the submission page so two people do not overwrite each other
- [ ] Submit before 11:59 pm local time, then download the participant certificate (PDF)

## Answers for the submission form (copy and paste)

**Project Name:** KAIRO

**Project Demonstration (link):**
https://github.com/likhitgv/Qubix/blob/main/FIELDWISE_AI/docs/demo/KAIRO_Demo.pdf
(7 slides. A YouTube link to `KAIRO_Demo_28s.mp4` also works; use one public link, no password.)

**Project (link to your project):** https://github.com/likhitgv/Qubix

**Project Details:**

KAIRO is a crop-planning tool for farmers and local agronomists in India. A user chooses a state and district (or drops a pin on a map) and answers three questions: soil type, how the field is irrigated, and what was grown before. KAIRO then recommends a two-season plan (kharif, then rabi) with a best option, the reasons it may fit, the main trade-off, and two alternatives.

How it works: we downloaded NASA POWER daily weather (temperature, rainfall, humidity) for 882 grid points covering India, 2021-2026, and turned it into seasonal summaries. Each field uses its nearest NASA grid cell, and past kharif and rabi seasons are averaged. These are compared with crop needs in a sourced crop database using transparent rule-based scoring, then combined into rotations (a bonus for including a legume, a penalty for repeating a crop family). Every score can be opened under "How this was calculated". A NASA GPM IMERG rainfall sample was used to cross-check rainfall.

Impact: it gives farmers local, plain-language guidance grounded in NASA data and shows its reasoning instead of acting as a black box. Saved plans let users return to earlier recommendations.

Tools: Python, Streamlit, pandas, Plotly, Folium with OpenStreetMap, SQLite, NASA POWER data, Census 2011 district boundaries.

Creativity: a guided four-question flow, a trade-off-first recommendation, and an honesty-first design: unverified crop data is flagged in the app, and KAIRO says it is decision support, not agronomic advice.

Limits: validated only in five Karnataka districts; six crops; some crop figures are still being verified; NASA POWER is modelled data for a ~56 km area, not a field measurement; no yield or savings claims are made.

AI use: built with Anthropic's Claude (Claude Code) assisting with code, tests and documentation. An optional feature can ask a hosted language model (Groq) to explain KAIRO's results; its text is accepted only if every number matches KAIRO's computed data.

**NASA Data links (Link Text / Link URL):**

| Link Text | Link URL |
|---|---|
| NASA POWER daily point and gridded data (temperature, rainfall, humidity) | https://power.larc.nasa.gov/ |
| NASA GPM IMERG Final V07B rainfall (January 2025 sample, cross-check) | https://gpm.nasa.gov/data/imerg |

**Space Agency Partner & Other Data (Link Text / Link URL):**

| Link Text | Link URL |
|---|---|
| India Census 2011 district boundaries (datameet) | https://github.com/datameet/maps |
| OpenStreetMap map tiles | https://www.openstreetmap.org/copyright |
| TNAU Agritech crop production guides (crop reference data) | https://agritech.tnau.ac.in/ |
| Streamlit (app framework) | https://streamlit.io/ |
