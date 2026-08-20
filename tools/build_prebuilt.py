#!/usr/bin/env python3
#
# Copyright (C) 2026 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
Build script for generating Torq prebuilts and distributable packages.

Outputs:
  - Universal Python Zipapp executable: dist/torq (or dist/torq.pyz)
  - Standalone OS-native binary (via PyInstaller if available): dist/torq-<platform>
  - Checksum manifest: dist/checksums.txt
"""

import argparse
import hashlib
import os
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
import zipapp

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, 'src')
MAIN_PY = os.path.join(ROOT_DIR, 'main.py')
DIST_DIR = os.path.join(ROOT_DIR, 'dist')


def get_platform_identifier():
  os_name = platform.system().lower()
  machine = platform.machine().lower()
  if os_name == 'darwin':
    os_name = 'darwin'
  elif os_name == 'linux':
    os_name = 'linux'
  elif os_name == 'windows':
    os_name = 'windows'

  if machine in ('x86_64', 'amd64'):
    arch = 'x86_64'
  elif machine in ('arm64', 'aarch64'):
    arch = 'arm64'
  else:
    arch = machine

  ext = '.exe' if os_name == 'windows' else ''
  return f"{os_name}-{arch}{ext}"


def calculate_sha256(filepath):
  sha256 = hashlib.sha256()
  with open(filepath, 'rb') as f:
    while chunk := f.read(65536):
      sha256.update(chunk)
  return sha256.hexdigest()


def build_universal_zipapp(dist_dir):
  """Builds a universal, self-contained executable Python zipapp."""
  os.makedirs(dist_dir, exist_ok=True)
  output_path = os.path.join(dist_dir, 'torq')

  with tempfile.TemporaryDirectory(prefix='torq_build_') as tmpdir:
    # Copy src directory
    shutil.copytree(
        SRC_DIR,
        os.path.join(tmpdir, 'src'),
        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))

    # Copy main.py as __main__.py for entry point
    shutil.copyfile(MAIN_PY, os.path.join(tmpdir, '__main__.py'))

    # Create zipapp with python3 shebang
    zipapp.create_archive(
        source=tmpdir,
        target=output_path,
        interpreter='/usr/bin/env python3',
        compressed=True)

  # Ensure executable permission
  current_mode = os.stat(output_path).st_mode
  os.chmod(output_path,
           current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

  # Also provide .pyz named copy for Windows / explicit Python execution
  pyz_path = os.path.join(dist_dir, 'torq.pyz')
  shutil.copyfile(output_path, pyz_path)

  print(
      f"[SUCCESS] Built Universal Zipapp: {output_path} ({os.path.getsize(output_path):,} bytes)"
  )
  return [output_path, pyz_path]


def build_standalone_binary(dist_dir):
  """Builds a standalone native binary using PyInstaller if installed."""
  os.makedirs(dist_dir, exist_ok=True)
  platform_id = get_platform_identifier()
  binary_name = f"torq-{platform_id}"
  output_binary = os.path.join(dist_dir, binary_name)

  pyinstaller_bin = shutil.which('pyinstaller')
  if not pyinstaller_bin:
    venv_pyinstaller = os.path.join(ROOT_DIR, '.venv', 'bin', 'pyinstaller')
    if os.path.exists(venv_pyinstaller):
      pyinstaller_bin = venv_pyinstaller

  if not pyinstaller_bin:
    print("[WARNING] PyInstaller not found. Skipping standalone binary build.")
    return []

  print(f"[INFO] Building standalone binary using {pyinstaller_bin}...")
  with tempfile.TemporaryDirectory(prefix='torq_pyinstaller_') as tmpdir:
    cmd = [
        pyinstaller_bin,
        '--onefile',
        '--name',
        'torq_standalone',
        '--distpath',
        dist_dir,
        '--workpath',
        os.path.join(tmpdir, 'build'),
        '--specpath',
        tmpdir,
        '--clean',
        MAIN_PY,
    ]
    subprocess.check_call(cmd, cwd=ROOT_DIR)

    generated_bin = os.path.join(
        dist_dir, 'torq_standalone.exe'
        if platform.system() == 'Windows' else 'torq_standalone')
    if os.path.exists(generated_bin):
      if os.path.exists(output_binary):
        os.remove(output_binary)
      os.rename(generated_bin, output_binary)
      print(
          f"[SUCCESS] Built Standalone Binary: {output_binary} ({os.path.getsize(output_binary):,} bytes)"
      )
      return [output_binary]
    else:
      print(f"[ERROR] Expected output binary not found at {generated_bin}")
      return []


def generate_checksums(dist_dir, built_files):
  """Generates a SHA256 checksum file for all built artifacts."""
  checksum_file = os.path.join(dist_dir, 'checksums.txt')
  with open(checksum_file, 'w') as f:
    for filepath in sorted(set(built_files)):
      if os.path.exists(filepath):
        rel_name = os.path.basename(filepath)
        sha = calculate_sha256(filepath)
        f.write(f"{sha}  {rel_name}\n")
  print(f"[SUCCESS] Generated Checksums: {checksum_file}")
  return checksum_file


def verify_artifact(artifact_path):
  """Runs smoke tests against built prebuilt."""
  print(f"[INFO] Verifying prebuilt {artifact_path}...")
  cmd_help = [artifact_path, '--help']
  if artifact_path.endswith('.pyz'):
    cmd_help = [sys.executable, artifact_path, '--help']

  res = subprocess.run(
      cmd_help, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
  if res.returncode != 0:
    print(
        f"[FAIL] Verification failed for {artifact_path} (returncode {res.returncode}):\n{res.stderr}"
    )
    return False

  if 'Torq CLI tool for performance tests' not in res.stdout:
    print(f"[FAIL] Verification output missing expected banner:\n{res.stdout}")
    return False

  # Test config list
  cmd_config = [artifact_path, 'config', 'list']
  if artifact_path.endswith('.pyz'):
    cmd_config = [sys.executable, artifact_path, 'config', 'list']
  res_config = subprocess.run(
      cmd_config, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
  if res_config.returncode != 0:
    print(
        f"[FAIL] Config list failed for {artifact_path}:\n{res_config.stderr}")
    return False

  print(f"[PASS] Successfully verified {artifact_path}")
  return True


def parse_args():
  parser = argparse.ArgumentParser(
      description="Build Torq prebuilts and packages.")
  parser.add_argument(
      '--dist-dir',
      default=DIST_DIR,
      help="Destination directory for built prebuilts.")
  parser.add_argument(
      '--standalone',
      action='store_true',
      help="Build PyInstaller standalone native binary.")
  parser.add_argument(
      '--universal-only',
      action='store_true',
      help="Build only universal zipapp prebuilt.")
  parser.add_argument(
      '--verify',
      action='store_true',
      default=True,
      help="Verify generated artifacts with smoke tests.")
  parser.add_argument(
      '--no-verify',
      dest='verify',
      action='store_false',
      help="Skip smoke verification.")
  return parser.parse_args()


def main():
  args = parse_args()
  dist_dir = os.path.abspath(args.dist_dir)
  built_artifacts = []

  # 1. Always build universal zipapp
  zipapp_files = build_universal_zipapp(dist_dir)
  built_artifacts.extend(zipapp_files)

  # 2. Build standalone binary if requested
  if args.standalone and not args.universal_only:
    standalone_files = build_standalone_binary(dist_dir)
    built_artifacts.extend(standalone_files)

  # 3. Generate checksums
  if built_artifacts:
    generate_checksums(dist_dir, built_artifacts)

  # 4. Verify artifacts
  if args.verify:
    all_passed = True
    for artifact in built_artifacts:
      if not verify_artifact(artifact):
        all_passed = False
    if not all_passed:
      print("[ERROR] One or more artifact verifications failed.")
      sys.exit(1)
    print("\n[ALL PREBUILTS BUILT AND VERIFIED SUCCESSFULLY]")


if __name__ == '__main__':
  main()
