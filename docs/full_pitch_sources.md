# Full-pitch video sources

This project should move v2 tracking tests away from broadcast clips with frequent
camera cuts. Fixed, panoramic, or full-pitch clips are a better fit for measuring
track continuity, team memory, and future possession logic.

## Preferred source: SoccerTrack v2

SoccerTrack v2 is the best match for the next experiments:

- 10 full-length panoramic 4K matches.
- Full-pitch coverage from fixed panoramic camera systems.
- Per-frame annotations with track IDs, roles, team assignments, and pitch
  coordinates.
- Ball action annotations that can become useful for v3/v4 validation.

Official sources:

- Landing page: https://atomscott.github.io/SoccerTrack-v2/
- GitHub: https://github.com/AtomScott/SoccerTrack-v2
- Hugging Face: https://huggingface.co/datasets/atomscott/soccertrack-v2
- Google Drive mirror: https://drive.google.com/drive/folders/1N2Qx2qkFgRtpbHitl2Vh6sLVYGgqkWwn

Current local status:

- Hugging Face access returns unauthorized from this machine without an
  authenticated token.
- The Google Drive mirror is visible in the browser, but scripted download may
  require a browser session or a shared direct file link.

Recommended first test:

1. Download one first-half or second-half panoramic MP4 from match `117093` or a
   held-out match such as `117099`.
2. Place it under `videos/external/soccertrack_v2/raw/`.
3. Cut several one-minute clips with `tools/create_video_clips.py`.

## Second source: TeamTrack / SoccerTrack classic

TeamTrack is useful if SoccerTrack v2 access is blocked. It contains full-pitch
team-sport videos, including soccer side/top views. It is published through
Kaggle and Google Drive.

Official sources:

- TeamTrack on Kaggle: https://www.kaggle.com/datasets/atomscott/teamtrack
- TeamTrack paper: https://arxiv.org/abs/2404.13868
- SoccerTrack classic on Kaggle: https://www.kaggle.com/datasets/atomscott/soccertrack

Current local status:

- The Kaggle CLI is not installed.
- No Kaggle credentials were found at `C:\Users\javie\.kaggle\kaggle.json`.

Recommended first test:

1. Download only the soccer subset if possible, preferably `soccer_side` first.
2. Place MP4 files under `videos/external/teamtrack/raw/`.
3. Cut one-minute clips for repeatable v2 tests.

## Third source: NPSPT

NPSPT is relevant because it is described as a non-professional soccer tracking
dataset recorded with a fixed wide-angle camera covering the whole field. It is
a good research reference, but a direct public video download path still needs
manual confirmation before we depend on it.

Reference:

- Paper: https://www.mdpi.com/2076-3417/12/15/7473

## SoccerNet fallback

SoccerNet remains useful for broadcast-view robustness and final report context,
but it is not the right main source for v2 tracker evaluation. If we keep using
SoccerNet, select only longer general-view passages and avoid clips with frequent
close-ups and camera cuts.
