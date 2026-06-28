# Publishing FloorTrades

Three things happen here: **(1)** build & push the Docker image, **(2)** publish
the community app store so you can install it, and **(3)** optionally submit to
the official Umbrel App Store.

Throughout, replace `YOU` with your GitHub username.

---

## 0. One-time prerequisites

- A GitHub account.
- A **Personal Access Token (classic)** with `write:packages` + `repo` scopes:
  https://github.com/settings/tokens  → save it somewhere safe.
- Docker with buildx (already on your Umbrel; commands below use `sudo`).

---

## 1. Build & push the multi-arch image to GHCR

```bash
# log in to GitHub Container Registry (paste the PAT as the password)
echo "<YOUR_PAT>" | sudo docker login ghcr.io -u YOU --password-stdin

# build for amd64 + arm64 and push
cd ~/floortrades
sudo -E GH_USER=YOU VERSION=1.0.0 ./scripts/build-and-push.sh

# make the package public so Umbrel can pull it:
#   github.com/users/YOU/packages/container/floortrades/settings → Change visibility → Public
```

> Tip: pin the digest printed at the end into
> `umbrel/floortrades/docker-compose.yml` (`image: ghcr.io/YOU/floortrades@sha256:…`)
> for reproducible installs.

---

## 2. Publish the community app store

The community store is a **separate git repo** whose root is the *contents* of
the `umbrel/` directory.

```bash
# create the store repo locally from the umbrel/ contents
rm -rf /tmp/floortrades-store && cp -r ~/floortrades/umbrel /tmp/floortrades-store
cd /tmp/floortrades-store
git init -b main
git add .
git commit -m "FloorTrades community app store v1.0.0"

# create the GitHub repo and push (needs the gh CLI, or create it in the web UI)
gh repo create floortrades-store --public --source=. --push
# …or without gh:
#   git remote add origin https://github.com/YOU/floortrades-store.git
#   git push -u origin main
```

Then on your Umbrel:
**Settings → App Store → Community App Stores → Add** → paste
`https://github.com/YOU/floortrades-store` → install **FloorTrades**.

---

## 3. (Optional) Submit to the official Umbrel App Store

```bash
gh repo fork getumbrel/umbrel-apps --clone
cd umbrel-apps
cp -r ~/floortrades/umbrel/floortrades ./floortrades   # app folder at repo root
git checkout -b add-floortrades
git add floortrades
git commit -m "Add FloorTrades — congressional stock-trading tracker"
git push -u origin add-floortrades
gh pr create --repo getumbrel/umbrel-apps \
  --title "Add FloorTrades" \
  --body-file ~/floortrades/.github/STORE_SUBMISSION.md
```

The official store requires the app to be open source, fully self-hosted, run on
amd64 + arm64, and work without editing config files — FloorTrades meets all of
these. Reviewers will also expect the `gallery/*.jpg` screenshots to be present.
