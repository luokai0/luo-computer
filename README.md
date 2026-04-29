# LUO COMPUTER

LUO COMPUTER is the runtime where the LUO OS swarm works on a visible computer surface.

## What it does
- 3-6 letter usernames only
- Consent-first onboarding
- 10,000 seeded agents split into roles and expertise
- Tasks that decompose into visible steps
- A local computer record with browser / terminal / files / computer surfaces
- A visible action log so the user can watch what the swarm is doing
- A cloned `luo_os/` tree inside the repo that the swarm imports and works against
- Per-user secrets, files, skills, projects, and device links

## How it starts
- Click 1: launch `luo-computer`
- Click 2: inside the app, press **Start Session**

LUO OS is embedded inside the session workspace. It is not treated as a separate portable add-on.

## Current prototype
The app is a C++20 core with a generated HTML dashboard and deterministic state model.
It is cross-platform by design and stores its state in the user data directory.
