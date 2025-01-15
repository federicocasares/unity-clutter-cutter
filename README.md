# Unity Clutter Cutter

A Python-based utility for finding potentially unused assets in Unity projects. This tool helps you identify and clean up unused assets by scanning through project files and checking for GUID references.

## Overview

Unity Clutter Cutter scans your Unity project for assets that are not being referenced by other assets in your project. It works by:
1. Collecting GUIDs from all the .meta files in the specified directory.
2. Searching through Unity asset files (like prefabs, scenes, materials) for references to these GUIDs.
3. Reporting assets from step 1 that have no references in any of the files gathered in step 2.

## Dependencies

The tool requires a decently modern version of Python 3 with the following packages installed:
- colorama
- tabulate
- tqdm
- humanize

## Usage

1. Clone or download this repository
2. Install the required dependencies
```
pip install colorama tabulate tqdm humanize
```
3. Run the script with the following command:
```
python find_unused.py -d <path_to_directory>
```

### Arguments
- `-d, --dir`: Path to the directory to check for unused assets (required)
- `-p, --processes`: Number of simultaneous processes to use (default: 8, range: 1-32)
- `-e, --extensions`: Specify which file extensions to check for references (default: .asset, .prefab, .mat, .unity, .shadergraph, .asmdef, .controller, .overridecontroller, .vfx)

## Important Warning!

This tool only checks for references in Unity asset files by comparing GUIDs. Assets that are only referenced via code (such as scripts, shaders, or resources loaded programmatically) will be reported as unused even if they are actually in use. Always verify results manually before deleting any assets!

## Motivation

This tool was born out of a real problem during the development of "Break, Enter, Repeat". During the early prototyping phase, I used lots of placeholder assets (textures, models, etc.) to test out game mechanics. As development progressed, these temporary assets were replaced with final, polished versions, but the old assets remained in the project. These poor forgotten files bloated the build size and wasted disk (flash?) space, and they also cluttered up the Unity Editor UI, making it harder to work with the assets actually in use.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
