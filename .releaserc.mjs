// Release configuration for the GitLab repository where this library is
// developed. Releases do not run on the GitHub mirror, so users of the library
// can ignore this file.
//
// The version comes from the conventional commits since the last tag.
// bump-my-version writes it into every file listed in .bumpversion.toml. The
// release notes are the hand-written `## [Unreleased]` section of CHANGELOG.md
// rather than the commit subjects, so what users read is the prose the merge
// request author wrote.

const publicRepositoryUrl = "https://github.com/DeepL/deepl-python";

// Prints the body of the `## [Unreleased]` section with surrounding blank lines
// trimmed. Used both to reject an empty release and as the release notes.
const unreleasedSection =
  "awk '/^## \\[Unreleased\\]/{f=1;next} /^## \\[/{f=0} f' CHANGELOG.md" +
  " | sed -e '/./,$!d' -e :a -e '/^\\n*$/{$d;N;};/\\n$/ba'";

// Refuse to guess the remote. Left unset, semantic-release falls back to the
// repository field of the package manifest, which points at the public GitHub
// mirror, and a local run would try to push a tag there.
const gitlabProjectUrl = process.env.CI_PROJECT_URL;
if (!gitlabProjectUrl) {
  throw new Error(
    "CI_PROJECT_URL is not set. Releases run in GitLab CI. To try this locally," +
      " set CI_PROJECT_URL to the GitLab project and pass --dry-run.",
  );
}

export default {
  branches: ["main"],
  repositoryUrl: `${gitlabProjectUrl}.git`,
  plugins: [
    [
      "@semantic-release/commit-analyzer",
      {
        preset: "conventionalcommits",
        releaseRules: [
          // A custom rule set replaces the default rules completely, so
          // breaking changes and reverts must be declared here. Without the
          // first rule a "feat!:" commit would release a minor.
          { breaking: true, release: "major" },
          { revert: true, release: "patch" },
          { type: "build", release: false },
          { type: "chore", release: false },
          { type: "ci", release: false },
          { type: "docs", release: false },
          { type: "refactor", release: false },
          { type: "style", release: false },
          { type: "test", release: false },
          { type: "feat", release: "minor" },
          { type: "fix", release: "patch" },
          { type: "perf", release: "patch" },
          { type: "patch", release: "patch" },
        ],
      },
    ],
    [
      "@semantic-release/exec",
      {
        // Runs before anything is written, so an empty changelog section stops
        // the release instead of publishing a version with no notes.
        verifyReleaseCmd:
          'test -n "$(' +
          unreleasedSection +
          ')" || { echo "CHANGELOG.md has no entries under ## [Unreleased]" >&2; exit 1; }',
        generateNotesCmd: unreleasedSection,
        // The URL is passed explicitly: keep-a-changelog otherwise derives the
        // changelog links from the git remote, which here is the internal one.
        prepareCmd: [
          "uvx bump-my-version bump --new-version ${nextRelease.version}",
          "npx --yes keep-a-changelog@2.8.0 --release ${nextRelease.version}" +
            " --url=" + publicRepositoryUrl,
          "npx --yes keep-a-changelog@2.8.0 --create --url=" + publicRepositoryUrl,
        ].join(" && "),
      },
    ],
    [
      "@semantic-release/git",
      {
        assets: [
          "CHANGELOG.md",
          ".bumpversion.toml",
          "pyproject.toml",
          "deepl/version.py",
          "tests/test_general.py",
        ],
        // The body is what .github/workflows/release.yml reads to fill the
        // GitHub release, so it must stay the changelog section.
        message: "chore(release): ${nextRelease.version}\n\n${nextRelease.notes}",
      },
    ],
    ["@semantic-release/gitlab", { gitlabUrl: "https://gitlab.com" }],
  ],
};
