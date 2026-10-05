<a id="readme-top"></a>

<!-- PROJECT SHIELDS -->
[![Python][python-shield]][python-url]
[![pytest][pytest-shield]][pytest-url]
[![Claude Code][claude-shield]][claude-url]
[![License: MIT][license-shield]][license-url]

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/gautierlp/magpie">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/assets/magpie-logo-dark.svg">
      <img src="docs/assets/magpie-logo.svg" alt="magpie" width="160" height="160">
    </picture>
  </a>

  <h1 align="center">magpie</h1>

  <p align="center">
    A magpie picks shiny bits from everywhere and keeps them in one nest.
    <br />
    This Claude Code skill does the same with your day.
    <br />
    <a href="#usage"><strong>See what it writes »</strong></a>
    <br />
    <br />
    <a href="skills/daily/SKILL.md">Read the skill</a>
    &middot;
    <a href="https://github.com/gautierlp/magpie/issues/new">Report bug</a>
    &middot;
    <a href="https://github.com/gautierlp/magpie/issues/new">Request feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About the project</a>
      <ul>
        <li><a href="#built-with">Built with</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
        <li><a href="#configuration">Configuration</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#how-it-works">How it works</a></li>
    <li><a href="#privacy">Privacy</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->
## About the project

I kept a three-line daily note in Obsidian: what I did, what blocked me, what comes
next. By 9 pm I could never remember half of what I did. The record already existed,
though. It sat in commit messages, in Claude Code transcripts, in my calendar, in the
mail I sent.

magpie collects those traces and drafts the note for you. You type `/daily` in the
evening, it reads the day, and it writes **Did:**, **Blocked:** and **Next:** into
that day's note. One bullet per project, each linked to the project's card in your
vault. You then edit the draft, which takes a minute instead of ten.

**Did:** is a record of facts. **Blocked:** and **Next:** are a first guess for you
to fix. magpie never invents a bullet: each one points back to a log, a commit, a
session, an event or a mail. If you already wrote some bullets yourself, magpie
keeps every fact in them and merges them into its draft.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built with

* [![Python][python-shield]][python-url]
* [![pytest][pytest-shield]][pytest-url]
* [![Claude Code][claude-shield]][claude-url]
* [just](https://github.com/casey/just) (command runner)

The script is standard-library Python with no runtime dependencies. `pytest` runs
the test suite and nothing else.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->
## Getting started

### Prerequisites

* Python 3.9 or newer
* [Claude Code](https://claude.com/claude-code), with session history under `~/.claude/projects/`
* An [Obsidian](https://obsidian.md) vault with a daily note that has `**Did:**`,
  `**Blocked:**` and `**Next:**` lines
* [just](https://github.com/casey/just), because the commands below use it

Each of these is optional and adds one source:

* [ActivityWatch](https://activitywatch.net), plus its browser extension for web time
* The Google Calendar connector in Claude
* A Google app password per Gmail account, for sent mail

### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/gautierlp/magpie.git
   cd magpie
   ```
2. Create a virtual environment and install the dev dependencies
   ```sh
   python3 -m venv .venv
   .venv/bin/pip install -r requirements-dev.txt
   ```
3. Run the tests, then install the skill
   ```sh
   just test
   just install
   ```
   `just install` copies `src/*.py` into `skills/daily/` and links that folder to
   `~/.claude/skills/daily`. After that, `/daily` works in any Claude Code session.

### Configuration

magpie reads `~/.config/magpie/config.json`, or the path in `$MAGPIE_CONFIG`. Every
key is optional, and an unknown key is an error, so a typo fails loudly.

```json
{
  "timezone": "Europe/Paris",
  "vault": "~/vault",
  "repos_root": "~/projects",
  "extra_repos": ["~/.claude"],
  "mail_accounts": ["you@example.com"],
  "calendars": ["you@example.com"],
  "exclude_domains": ["mybank.com"]
}
```

| Key | Default | What it does |
|---|---|---|
| `timezone` | system local | the IANA zone that defines "today" |
| `vault` | `~/vault` | your Obsidian vault |
| `journal_dir` | `50 Journal/daily` | daily notes folder, inside the vault |
| `template` | `90 Templates/daily.md` | template for a note that does not exist yet |
| `repos_root` | `~/projects` | every git repo directly under it is read |
| `extra_repos` | `[]` | more repos, anywhere |
| `activitywatch_url` | `http://localhost:5600/api/0` | the ActivityWatch API |
| `exclude_domains` | `[]` | sites never reported, subdomains included |
| `mail_accounts` | `[]` | Gmail addresses whose sent mail is read |
| `calendars` | `[]` | Google Calendar IDs |

For each mail account, create a Google app password and store it in the macOS
Keychain. The command asks for the password, so it never lands in your shell
history:

```sh
security add-generic-password -s daily-imap -a you@example.com -w
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- USAGE -->
## Usage

In any Claude Code session:

```
/daily              # today
/daily 2026-10-04   # an earlier day
```

A draft looks like this:

```markdown
**Did:**

- [[10 Projects/website/_project|website]]: rewrote the pricing page and fixed the mobile menu
- [[20 Areas/homelab/_area|homelab]]: moved the backups to the new disk, first full run took 2 h
- 14:00 call with Sam about the Q4 roadmap

**Blocked:**

- [[10 Projects/website/_project|website]]: waiting on Sam for the final prices

**Next:**

- [[10 Projects/website/_project|website]]: ship the pricing page once the prices land
```

If a source is missing (ActivityWatch is off, a mail password is not set), magpie
says so in one line and drafts from the rest.

You can also run the collector alone and read its JSON, without Claude and without
writing anything:

```sh
python3 src/daily.py gather --date 2026-10-05
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- HOW IT WORKS -->
## How it works

Two halves: a script that collects facts, and a skill that writes the bullets.

1. **Gather** (`src/daily.py gather`) prints one JSON object for the day, grouped by
   project card. Each source has its own module:
   * `daily_vault.py` reads every `_project.md` and `_area.md` card, and the day's
     `log/YYYY-MM-DD.md` files. A card's `repo:` line maps commits and sessions to it.
   * `daily_git.py` lists your commits of the day on all branches, from local clones.
   * `daily_sessions.py` reads Claude Code transcripts: your messages and the last
     reply of each session. A session that already wrote that day's vault log is
     skipped, since the log describes it better.
   * `daily_aw.py` sums ActivityWatch time when you were at the keyboard, by app and
     by web domain.
   * `daily_mail.py` reads sent mail headers over IMAP: recipients and subject.

   A failing source never stops the run. The payload lists it under `errors`.
2. **Draft** (the `daily` skill) reads the payload and the day's calendar, writes the
   bullets, and merges the ones you wrote by hand.
3. **Write** (`src/daily.py write`) replaces the three sections of the note and
   leaves the rest of the file untouched. It refuses to write an empty **Did:**.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- PRIVACY -->
## Privacy

The collector runs on your machine. The draft goes through Claude like any other
Claude Code message, so treat it as you treat your sessions.

* Mail: headers only. The IMAP fetch uses `BODY.PEEK[HEADER.FIELDS (DATE TO SUBJECT)]`,
  so it never downloads a body and never marks a mail as read.
* Web: domains only, never full URLs. Incognito tabs are skipped. Window titles from
  browsers are dropped, because the exclude list can only filter domains.
* Transcripts: read, never changed.
* Passwords: in the Keychain, never in a file.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ROADMAP -->
## Roadmap

- [x] Vault logs, git commits, Claude Code sessions
- [x] ActivityWatch with privacy filters
- [x] Sent mail headers over IMAP, Google Calendar through the connector
- [x] Merge of hand-written bullets
- [ ] Filter one-time codes out of window and tab titles
- [ ] A weekly summary built from the daily notes
- [ ] Linux keyring support for mail passwords

See the [open issues](https://github.com/gautierlp/magpie/issues) for the rest.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTRIBUTING -->
## Contributing

Contributions are welcome. The project uses TDD: write the test, watch it fail, then
write the code. Run the suite before you open a PR.

```sh
just test          # or: .venv/bin/pytest -v
```

1. Fork the project
2. Create your feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a pull request

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- LICENSE -->
## License

Distributed under the MIT License. See [`LICENSE`](LICENSE).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTACT -->
## Contact

Gautier Le Poher - gautier@lepoher.co

Project link: [https://github.com/gautierlp/magpie](https://github.com/gautierlp/magpie)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* [ActivityWatch](https://activitywatch.net)
* [Claude Code](https://claude.com/claude-code)
* [just](https://github.com/casey/just)
* [Shields.io](https://shields.io)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
[python-shield]: https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white
[python-url]: https://www.python.org/
[pytest-shield]: https://img.shields.io/badge/pytest-tested-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white
[pytest-url]: https://docs.pytest.org/
[claude-shield]: https://img.shields.io/badge/Claude%20Code-skill-D97757?style=for-the-badge&logo=anthropic&logoColor=white
[claude-url]: https://claude.com/claude-code
[license-shield]: https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge
[license-url]: #license
