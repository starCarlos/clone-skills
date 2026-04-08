---
name: multi-search-engine
description: Local bundled copy of the multi-search-engine search skill for networked search inside mind-clone-creator. Use for profession research, public-information lookup, knowledge-material discovery, skill discovery, and any other web-search task in this workflow.
---

# Multi Search Engine

## Purpose

This is the bundled internal copy of `multi-search-engine` for `mind-clone-creator`.
All networked search tasks in this workflow should follow this local copy instead of assuming the user has the external skill installed.

## Source

- Original listing: `https://clawhub.ai/gpyAngyoujun/multi-search-engine`
- Verified summary: `https://useclaw.pro/skills/multi-search-engine`
- Local copy captured for this skill on: `2026-03-12`

## What It Is For

Use this bundled copy whenever `mind-clone-creator` needs web search for:

- profession and workflow background research
- public-information lookup related to the user's own work context
- knowledge-material discovery
- skill discovery before installation
- multilingual search across Chinese and global sources
- time-bounded search such as recent updates

## Engines

### Domestic

- Baidu
- Bing CN
- Bing INT
- 360
- Sogou
- WeChat search
- Toutiao search
- Jisilu

### International

- Google
- Google HK
- DuckDuckGo
- Yahoo
- Startpage
- Brave
- Ecosia
- Qwant
- WolframAlpha

## Query Patterns

- Basic keyword search
- `site:` for site-specific search
- `filetype:` for document discovery
- exact match with quotes
- exclusion with `-`
- `OR` alternatives
- recent-time filters such as past day, week, month, year

## Use Rules Inside mind-clone-creator

1. Treat this local copy as the default network-search helper for the whole skill.
2. Use it before considering any other web-search helper.
3. If the user's workflow needs a stronger or different network capability than this bundled copy supports, identify the gap and ask the user before installing anything else.
4. External research found through this helper may enrich the workflow, but never override the user's own answers.
5. For high-stakes or time-sensitive questions, prefer narrower queries and source verification rather than broad search.

## Example Search Tasks

- Find profession-specific frameworks and work patterns
- Find public docs or articles the user wants to include as supporting materials
- Search for installable skills that match a workflow gap
- Search recent information that affects the user's domain

## Notes

- The verified public description says this skill supports 17 engines, advanced operators, time filters, privacy engines, and WolframAlpha queries without API keys.
- In `mind-clone-creator`, this bundled copy is used as an internal reference and routing policy for all web-search tasks.
