import json
import os
import urllib.request
from datetime import datetime, timezone

USERNAME = os.environ.get("GITHUB_USERNAME", "ssSobuj")
TOKEN = os.environ.get("GITHUB_TOKEN")

if not TOKEN:
    raise RuntimeError("GITHUB_TOKEN is not available.")

QUERY = """
query($login: String!) {
  user(login: $login) {
    login
    name
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            weekday
          }
        }
      }

      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount

      commitContributionsByRepository(maxRepositories: 10) {
        repository {
          name
          nameWithOwner
          url
        }
        contributions {
          totalCount
        }
      }
    }
  }
}
"""

payload = json.dumps({
    "query": QUERY,
    "variables": {
        "login": USERNAME
    }
}).encode("utf-8")

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    method="POST",
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": USERNAME,
    },
)

with urllib.request.urlopen(request) as response:
    result = json.loads(response.read().decode("utf-8"))

if "errors" in result:
    raise RuntimeError(json.dumps(result["errors"], indent=2))

user = result["data"]["user"]

if not user:
    raise RuntimeError(f"GitHub user '{USERNAME}' was not found.")

collection = user["contributionsCollection"]
calendar = collection["contributionCalendar"]

total_contributions = calendar["totalContributions"]
commits = collection["totalCommitContributions"]
issues = collection["totalIssueContributions"]
pull_requests = collection["totalPullRequestContributions"]
reviews = collection["totalPullRequestReviewContributions"]
restricted = collection["restrictedContributionsCount"]

weeks = calendar["weeks"]

days = []

for week in weeks:
    for day in week["contributionDays"]:
        days.append(day)

days.sort(key=lambda item: item["date"])

# ---------------------------------------------------------
# Calculate active days
# ---------------------------------------------------------

active_days = sum(
    1 for day in days
    if day["contributionCount"] > 0
)

# ---------------------------------------------------------
# Calculate current streak
# ---------------------------------------------------------

current_streak = 0

for day in reversed(days):
    if day["contributionCount"] > 0:
        current_streak += 1
    else:
        break

# ---------------------------------------------------------
# Calculate longest streak
# ---------------------------------------------------------

longest_streak = 0
streak = 0

for day in days:
    if day["contributionCount"] > 0:
        streak += 1
        longest_streak = max(longest_streak, streak)
    else:
        streak = 0

# ---------------------------------------------------------
# Repository ranking
# ---------------------------------------------------------

repositories = []

for item in collection["commitContributionsByRepository"]:
    repo = item["repository"]
    count = item["contributions"]["totalCount"]

    repositories.append({
        "name": repo["name"],
        "full_name": repo["nameWithOwner"],
        "url": repo["url"],
        "count": count,
    })

repositories.sort(
    key=lambda item: item["count"],
    reverse=True
)

repositories = repositories[:5]

# ---------------------------------------------------------
# Contribution color
# ---------------------------------------------------------

def contribution_color(count):
    if count == 0:
        return "#161b22"

    if count <= 2:
        return "#0e4429"

    if count <= 5:
        return "#006d32"

    if count <= 9:
        return "#26a641"

    return "#39d353"


# ---------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------

def escape(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


WIDTH = 1100
HEIGHT = 650

svg = []

svg.append(
    f'''<svg xmlns="http://www.w3.org/2000/svg"
    width="{WIDTH}"
    height="{HEIGHT}"
    viewBox="0 0 {WIDTH} {HEIGHT}">
'''
)

svg.append(
    '''
<rect
  width="100%"
  height="100%"
  rx="16"
  fill="#0d1117"
/>
'''
)

# ---------------------------------------------------------
# Title
# ---------------------------------------------------------

svg.append(
    '''
<text
  x="45"
  y="55"
  fill="#f0f6fc"
  font-family="Arial, Helvetica, sans-serif"
  font-size="26"
  font-weight="700">
  GitHub Activity
</text>
'''
)

svg.append(
    f'''
<text
  x="45"
  y="83"
  fill="#8b949e"
  font-family="Arial, Helvetica, sans-serif"
  font-size="15">
  @{escape(USERNAME)} • Real GitHub contribution data
</text>
'''
)

# ---------------------------------------------------------
# Statistic cards
# ---------------------------------------------------------

stats = [
    ("Contributions", total_contributions),
    ("Commits", commits),
    ("Pull Requests", pull_requests),
    ("Issues", issues),
    ("Active Days", active_days),
    ("Current Streak", current_streak),
    ("Longest Streak", longest_streak),
    ("Reviews", reviews),
]

card_width = 245
card_height = 80
gap = 15

start_x = 45
start_y = 110

for index, (label, value) in enumerate(stats):
    row = index // 4
    column = index % 4

    x = start_x + column * (card_width + gap)
    y = start_y + row * (card_height + gap)

    svg.append(
        f'''
<rect
  x="{x}"
  y="{y}"
  width="{card_width}"
  height="{card_height}"
  rx="10"
  fill="#161b22"
  stroke="#30363d"
/>
'''
    )

    svg.append(
        f'''
<text
  x="{x + 18}"
  y="{y + 31}"
  fill="#8b949e"
  font-family="Arial, Helvetica, sans-serif"
  font-size="13">
  {escape(label)}
</text>
'''
    )

    svg.append(
        f'''
<text
  x="{x + 18}"
  y="{y + 61}"
  fill="#f0f6fc"
  font-family="Arial, Helvetica, sans-serif"
  font-size="23"
  font-weight="700">
  {escape(value)}
</text>
'''
    )

# ---------------------------------------------------------
# Contribution graph
# ---------------------------------------------------------

graph_x = 45
graph_y = 310

svg.append(
    '''
<text
  x="45"
  y="295"
  fill="#f0f6fc"
  font-family="Arial, Helvetica, sans-serif"
  font-size="18"
  font-weight="700">
  Contribution Activity
</text>
'''
)

# GitHub calendar is arranged as weeks.
# Draw the latest 53 weeks.

weeks_to_draw = weeks[-53:]

cell_size = 12
cell_gap = 3

for week_index, week in enumerate(weeks_to_draw):

    x = graph_x + week_index * (cell_size + cell_gap)

    for day in week["contributionDays"]:

        weekday = day["weekday"]
        count = day["contributionCount"]

        y = graph_y + weekday * (cell_size + cell_gap)

        svg.append(
            f'''
<rect
  x="{x}"
  y="{y}"
  width="{cell_size}"
  height="{cell_size}"
  rx="3"
  fill="{contribution_color(count)}">
  <title>{escape(day["date"])}: {count} contributions</title>
</rect>
'''
        )

# ---------------------------------------------------------
# Repository section
# ---------------------------------------------------------

repo_x = 760
repo_y = 390

svg.append(
    f'''
<text
  x="{repo_x}"
  y="{repo_y}"
  fill="#f0f6fc"
  font-family="Arial, Helvetica, sans-serif"
  font-size="18"
  font-weight="700">
  Top Active Repositories
</text>
'''
)

if repositories:

    for index, repo in enumerate(repositories):

        y = repo_y + 35 + index * 38

        repo_name = repo["name"]

        if len(repo_name) > 25:
            repo_name = repo_name[:22] + "..."

        svg.append(
            f'''
<circle
  cx="{repo_x + 6}"
  cy="{y - 5}"
  r="4"
  fill="#39d353"
/>
'''
        )

        svg.append(
            f'''
<text
  x="{repo_x + 20}"
  y="{y}"
  fill="#c9d1d9"
  font-family="Arial, Helvetica, sans-serif"
  font-size="14">
  {escape(repo_name)}
</text>
'''
        )

        svg.append(
            f'''
<text
  x="{repo_x + 270}"
  y="{y}"
  fill="#8b949e"
  font-family="Arial, Helvetica, sans-serif"
  font-size="13"
  text-anchor="end">
  {repo["count"]} commits
</text>
'''
        )

else:

    svg.append(
        f'''
<text
  x="{repo_x}"
  y="{repo_y + 35}"
  fill="#8b949e"
  font-family="Arial, Helvetica, sans-serif"
  font-size="14">
  No repository data available.
</text>
'''
    )

# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------

generated_at = datetime.now(timezone.utc).strftime(
    "%Y-%m-%d %H:%M UTC"
)

svg.append(
    f'''
<text
  x="45"
  y="625"
  fill="#6e7681"
  font-family="Arial, Helvetica, sans-serif"
  font-size="12">
  Updated automatically • {escape(generated_at)}
</text>
'''
)

svg.append("</svg>")

# ---------------------------------------------------------
# Write SVG
# ---------------------------------------------------------

os.makedirs("profile", exist_ok=True)

output_file = "profile/github-activity.svg"

with open(output_file, "w", encoding="utf-8") as file:
    file.write("".join(svg))

print(f"Generated {output_file}")
print(f"Total contributions: {total_contributions}")
print(f"Commits: {commits}")
print(f"Pull requests: {pull_requests}")
print(f"Issues: {issues}")
print(f"Reviews: {reviews}")
print(f"Active days: {active_days}")
print(f"Current streak: {current_streak}")
print(f"Longest streak: {longest_streak}")
