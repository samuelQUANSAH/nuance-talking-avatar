"""
Automated deployment script to create and deploy the Nuance Talking Avatar
(LivePortrait + Nuance micro-expression controls) to Hugging Face Spaces.
"""
import os
import sys
from pathlib import Path
import shutil

try:
    from huggingface_hub import HfApi, get_token, snapshot_download
except ImportError:
    print("Error: huggingface_hub is not installed in the active environment.")
    sys.exit(1)


def check_auth():
    token = os.environ.get("HF_TOKEN") or get_token()
    if not token:
        # Check ~/.cache/huggingface/token or ~/.env
        cache_token = Path.home() / ".cache" / "huggingface" / "token"
        if cache_token.exists():
            token = cache_token.read_text().strip()
        elif (Path.home() / ".env").exists():
            for line in (Path.home() / ".env").read_text().splitlines():
                if line.startswith("HF_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                    break

    if not token:
        print("[!] No Hugging Face token detected.")
        return None, None

    api = HfApi(token=token)
    try:
        user_info = api.whoami()
        username = user_info.get("name")
        print(f"[✓] Authenticated with Hugging Face as: @{username}")
        return api, username
    except Exception as e:
        print(f"[!] Authentication failed with provided token: {e}")
        return None, None


def prepare_space_directory(dest_dir: Path, source_avatar: Path):
    print(f"[*] Preparing Space build directory at: {dest_dir}")
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # 1. Create Space README.md (frontmatter)
    readme_content = """---
title: Nuance Talking Avatar (LivePortrait)
emoji: 🎭
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 4.38.0
app_file: app.py
pinned: false
suggested_hardware: t4-small
---

# Nuance Talking Avatar (LivePortrait)

Real-time expressive facial animation and conversational micro-expression synthesis powered by LivePortrait and Nuance-style active listening retargeting.
"""
    (dest_dir / "README.md").write_text(readme_content)

    # 2. requirements.txt
    requirements = """torch>=2.2.0
torchvision
gradio>=4.38.0
numpy<2.0.0
opencv-python-headless
onnx
onnxruntime-gpu
diffusers
transformers
accelerate
safetensors
imageio
imageio-ffmpeg
scipy
tyro
huggingface_hub
pyyaml
"""
    (dest_dir / "requirements.txt").write_text(requirements)

    # 3. packages.txt
    packages = """ffmpeg
libgl1-mesa-glx
libglib2.0-0
"""
    (dest_dir / "packages.txt").write_text(packages)

    # 4. Copy src code
    shutil.copytree("src", dest_dir / "src", dirs_exist_ok=True)

    # 5. Copy assets (including sample source and driving templates)
    assets_dest = dest_dir / "assets"
    shutil.copytree("assets", assets_dest, dirs_exist_ok=True)

    # Ensure user avatar is copied as the primary default source
    source_target = assets_dest / "examples" / "source" / "avatar_source.jpg"
    source_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(source_avatar, source_target)

    # 6. Adapt app.py for Space execution (auto weight download)
    app_source = Path("app.py").read_text()
    
    # Prepend weight download logic if missing
    auto_download_header = '''# coding: utf-8
import os
import os.path as osp

# Automatic weight check & download for Hugging Face Spaces
if not osp.exists("pretrained_weights") or not osp.exists("pretrained_weights/liveportrait"):
    print("[HF Space Boot] Downloading LivePortrait weights from KlingTeam/LivePortrait...")
    from huggingface_hub import snapshot_download
    snapshot_download(
        repo_id="KlingTeam/LivePortrait",
        local_dir="pretrained_weights",
        ignore_patterns=["*.git*", "README.md", "docs/*", "*animals*"],
        local_dir_use_symlinks=False,
    )
    print("[HF Space Boot] Weights successfully initialized.")

'''
    # Replace existing coding header or prepend
    if app_source.startswith("# coding: utf-8"):
        app_source = app_source.replace("# coding: utf-8\n", auto_download_header, 1)
    else:
        app_source = auto_download_header + app_source

    # Inject user avatar as top example in data_examples_i2v
    if 'data_examples_i2v = [' in app_source:
        app_source = app_source.replace(
            'data_examples_i2v = [',
            'data_examples_i2v = [\n    [osp.join(example_portrait_dir, "avatar_source.jpg"), osp.join(example_video_dir, "d0.mp4"), True, True, True, False],'
        )

    (dest_dir / "app.py").write_text(app_source)
    print(f"[✓] Space build directory prepared successfully with {len(list(dest_dir.rglob('*')))} files.")


def deploy(space_name: str = "nuance-talking-avatar"):
    api, username = check_auth()
    if not api or not username:
        print("\n[!] Cannot deploy without Hugging Face authentication.")
        print("Please authenticate using the secure terminal command provided.")
        return False

    repo_id = f"{username}/{space_name}"
    print(f"[*] Target Space: https://huggingface.co/spaces/{repo_id}")

    # Create repo if not exists
    try:
        api.create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="gradio",
            exist_ok=True
        )
        print(f"[✓] Space repository confirmed: {repo_id}")
    except Exception as e:
        print(f"[!] Error creating/accessing Space repo: {e}")
        return False

    # Prepare local package
    build_dir = Path("build_hf_space")
    user_avatar = Path("assets/examples/source/avatar_source.jpg")
    prepare_space_directory(build_dir, user_avatar)

    # Upload files to Space
    print(f"[*] Uploading files to Hugging Face Space ({repo_id})...")
    try:
        api.upload_folder(
            folder_path=str(build_dir),
            repo_id=repo_id,
            repo_type="space",
            commit_message="feat: deploy Nuance talking avatar with active listening retargeting"
        )
        print(f"\n=======================================================")
        print(f"[🎉] Deployment initiated successfully!")
        print(f"Space URL: https://huggingface.co/spaces/{repo_id}")
        print(f"=======================================================")
        return True
    except Exception as e:
        print(f"[!] Upload failed: {e}")
        return False


if __name__ == "__main__":
    deploy()
