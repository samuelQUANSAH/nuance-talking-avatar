"""
Script to download LivePortrait pretrained weights cleanly using huggingface_hub.
"""
import os
import sys
from huggingface_hub import snapshot_download

def main():
    target_dir = os.path.abspath("pretrained_weights")
    os.makedirs(target_dir, exist_ok=True)
    print(f"Downloading LivePortrait weights into {target_dir}...")
    
    # Download human models (insightface, liveportrait base models, retargeting models)
    snapshot_download(
        repo_id="KlingTeam/LivePortrait",
        local_dir=target_dir,
        ignore_patterns=["*.git*", "README.md", "docs/*", "*animals*"],
        local_dir_use_symlinks=False,
    )
    print("Download completed successfully!")

if __name__ == "__main__":
    main()
