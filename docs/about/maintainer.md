---
title: Maintainer, GitHub Pages, Search, and Release Operations
description: Maintainer identity, repository metadata, GitHub Pages deployment, Search Console, crawler checks, and PyPI release operations.
---

# Maintainer and Site Operations

The public project identity is
[flavvesResearch](https://github.com/flavvesResearch). No personal author name
is inferred or published by this documentation.

## Repository metadata to set

These GitHub settings require repository administration access and are not
stored in source files.

**Description**

```text
Validate OpenCV checkerboard camera-calibration datasets for blur, coverage, pose diversity, duplicates, and reprojection error.
```

**Topics**

```text
opencv
camera-calibration
computer-vision
checkerboard
dataset-quality
reprojection-error
camera-intrinsics
python
```

**Homepage**

```text
https://flavvesresearch.github.io/opencv-calibration-audit/
```

## Deploy GitHub Pages

The repository's `Documentation` workflow:

1. builds MkDocs with strict warnings on pull requests;
2. uploads a Pages artifact after a non-PR build;
3. deploys only from the `main` branch;
4. uses job-scoped minimum permissions.

In GitHub repository settings, choose **GitHub Actions** as the Pages source.
After the first deployment, verify:

```text
https://flavvesresearch.github.io/opencv-calibration-audit/
https://flavvesresearch.github.io/opencv-calibration-audit/sitemap.xml
https://flavvesresearch.github.io/opencv-calibration-audit/guide/validate-opencv-camera-calibration-dataset/
```

## Configure Google Search Console

1. Add
   `https://flavvesresearch.github.io/opencv-calibration-audit/` as a URL-prefix
   property.
2. Download the HTML verification file from Search Console.
3. Place that exact file at the `docs/` root, commit it, and let the
   documentation workflow deploy it.
4. Submit
   `https://flavvesresearch.github.io/opencv-calibration-audit/sitemap.xml`.
5. Use URL Inspection to request indexing for the home page and main
   dataset-validation guide.

Search indexing and structured data do not guarantee ranking.

## Verify ChatGPT Search access

The published pages are static HTML with no login or client-side rendering
requirement. After deployment:

1. check the GitHub Pages domain-root `robots.txt` response;
2. confirm it does not disallow `OAI-SearchBot`;
3. confirm the hosting layer does not block OpenAI's published crawler IPs;
4. request the home page and guide with a normal HTTP client and verify `200`
   responses.

For a GitHub Pages project site, a `robots.txt` under the repository subpath
does not control the domain root. This repository therefore does not add a
misleading project-level file.

`OAI-SearchBot` supports ChatGPT Search discovery. `GPTBot` concerns potential
model training and can be managed independently. An `llms.txt` file is not a
replacement for accessible content, normal links, canonical URLs, or a
sitemap.

See [OpenAI crawler documentation](https://developers.openai.com/api/docs/bots)
and [ChatGPT Search guidance](https://help.openai.com/en/articles/9237897-chatgpt-search).

## Complete the 0.2.2 release

After repository changes pass CI:

1. publish version `0.2.2` through the existing GitHub Release and PyPI Trusted
   Publishing workflow;
2. verify PyPI metadata exposes keywords and Documentation, Repository,
   Changelog, and Issues links;
3. confirm the README's absolute report links work on PyPI;
4. keep `0.2.0` and `0.2.1`;
5. yank `0.1.0.post9`, `0.1.0.post10`, and `0.1.2` with reason:
   `Development scaffolding; use 0.2.0 or newer`.

Yanking is a reversible PyPI-owner action and is not performed by the
documentation workflow.

## Technical sharing principles

Publish the main guide first and a real production benchmark only after a
licensed dataset exists. When answering a relevant OpenCV Forum, Stack
Overflow, or computer-vision community question, make the answer independently
useful and link only where the audit directly supports the explanation. Do not
create promotional questions, duplicate posts, or claims of guaranteed
calibration quality.

_Documentation version: 0.2.2 · Updated: 2026-07-31_
