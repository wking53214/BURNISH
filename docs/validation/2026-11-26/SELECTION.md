# Outside validation, 2026-11-26: how the five repositories were chosen

The rule below was written before any repository was chosen or run. It was applied by a script, in order, and every
package looked at is listed with the reason it was taken or skipped.

## The rule

1. Walk hugovk/top-pypi-packages, top-pypi-packages-30-days.min.json at commit 29c0d4c38c28c0e6b99e73fa09cb91a2323ca51b, in download order.
2. Take the package's source repository from its PyPI project URLs (Source, Repository, Code, Homepage, in that order), only if it is on github.com.
3. Accept it if the repository is public, is not owned by wking53214, and its default branch has README.md and pyproject.toml at the root and at least one Python file.
4. At most one repository per GitHub owner: a later package from an owner already taken is skipped.
5. Stop at five. Record every package looked at and why it was skipped.

## The walk

| Rank | Package | Result |
|---|---|---|
| 1 | boto3 | skip: boto/boto3 has no README.md at the root |
| 2 | packaging | skip: pypa/packaging has no README.md at the root |
| 3 | typing-extensions | taken: python/typing_extensions at 7cfb2aed844b19b84d307e5953f32c0f4ec1a737 |
| 4 | certifi | skip: certifi/python-certifi has no README.md at the root |
| 5 | idna | taken: kjd/idna at d357725082245ff90f5cf8800a3fc297b1f2319a |
| 6 | urllib3 | taken: urllib3/urllib3 at 3db5970fcc56666ed5e7d450816ece9cce55589f |
| 7 | charset-normalizer | taken: jawah/charset_normalizer at 0b45fe26ec06006533c4b038fe239a01957e9d71 |
| 8 | requests | taken: psf/requests at 3c7baaa05ab4aa49cc819ce3a819d260de19c157 |

## The run

Burnish 0.5.3 (main at `a7b0cdc107cb2e53ea0e95ddb89f22f2ebe123a2`), run on 2026-11-26 after the five were chosen:
`burnish check`, `burnish critic` and `burnish readme-critic` (minimum tier) on each repository at the commit above, with
no `--collected` count, as someone trying Burnish for the first time would run it. Each output is in this folder as
`<repository>.<command>.txt`, with the exit code at the top; the scratch folder path is replaced by `owner/repository`.
