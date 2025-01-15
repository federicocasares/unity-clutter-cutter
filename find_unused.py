"""Unity Clutter Cutter - Find unused assets in Unity projects."""

import os
import argparse
import re
from multiprocessing import Pool
from pathlib import Path
from colorama import init, Fore, Style
from tabulate import tabulate
from tqdm import tqdm
from humanize import naturalsize

init()

# File extensions to check for references
# Customise this list according to the kind of assets you have in your project!
DEFAULT_EXTENSIONS_TO_CHECK = [
    ".asset",
    ".prefab",
    ".mat",
    ".unity",
    ".shadergraph",
    ".asmdef",
    ".controller",
    ".overridecontroller",
    ".vfx",
]


def print_banner():
    """Print the welcome banner when the tool starts"""
    banner = (
        "╔═════════════════════════════════════════════╗\n"
        + "║       Welcome to Unity Clutter Cutter       ║\n"
        + "╚═════════════════════════════════════════════╝"
    )
    print(f"{Fore.CYAN}{banner}{Style.RESET_ALL}")


def find_assets_dir(start_path):
    """Find the Assets directory by going up the directory tree"""
    current = Path(start_path).resolve()
    while current.parent != current:  # Stop at root directory
        if (current / "Assets").is_dir():
            return current / "Assets"
        current = current.parent
    raise FileNotFoundError("Could not find Assets directory in parent directories")


def find_assets_to_check(dir_path):
    """Collect all assets in the specified directory and return a dict of GUIDs to asset paths"""
    assets_to_check = {}
    for root, _, files in os.walk(dir_path):
        for file in files:
            if file.endswith(".meta"):
                asset_path = os.path.join(root, file[:-5])  # Remove .meta extension
                if os.path.exists(asset_path) and not os.path.isdir(asset_path):
                    guid = get_guid_from_meta(os.path.join(root, file))
                    if guid:
                        assets_to_check[guid] = asset_path
    return assets_to_check


def get_guid_from_meta(meta_file_path):
    """Extract and return the GUID from a .meta file"""
    try:
        with open(meta_file_path, "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r"guid: ([a-f0-9]{32})", content)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"Error reading meta file {meta_file_path}: {e}")
    return None


def collect_searchable_files(assets_dir, extensions_to_check):
    """Collect all files that need to be searched for GUID references"""
    searchable_files = []
    lowercase_extensions = [ext.lower() for ext in extensions_to_check]
    for root, _, files in os.walk(assets_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in lowercase_extensions):
                file_path = os.path.join(root, file)
                try:
                    # Try to open the file to verify it's readable text
                    with open(file_path, "r", encoding="utf-8") as f:
                        searchable_files.append(file_path)
                except Exception:
                    # Skip files that can't be read as text
                    continue
    return searchable_files


def find_references_to_guid(args):
    """Search for GUID references in the pre-collected list of files"""
    guid, searchable_files, asset_path = args
    for file_path in searchable_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                if guid in content:
                    return (asset_path, True)
        except Exception:
            # Skip if we suddenly can't read the file or it's not a text file
            continue
    return (asset_path, False)


def main():
    """Main function to run the tool"""
    print_banner()
    parser = argparse.ArgumentParser(description="Find unused Unity assets in a directory")
    parser.add_argument("-d", "--dir", required=True, help="Path to the directory to check for unused assets")
    parser.add_argument(
        "-p",
        "--processes",
        type=int,
        default=8,
        help="Number of simultaneous processes to use for parallel searching (1-32, default 8)",
    )
    parser.add_argument(
        "-e",
        "--extensions",
        nargs="+",
        default=DEFAULT_EXTENSIONS_TO_CHECK,
        help="Specify file extensions that will be checked for references (e.g., -e .prefab .mat .unity)",
    )
    args = parser.parse_args()

    if args.processes < 1 or args.processes > 32:
        print("Error: Invalid number of processes. Please use a value between 1 and 32.")
        return

    # Verify the specified directory exists
    if not os.path.isdir(args.dir):
        print(f"Error: Directory '{args.dir}' does not exist")
        return

    # Find the Assets directory
    try:
        assets_dir = find_assets_dir(args.dir)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    # Get all assets and their GUIDs from the specified directory
    print("Collecting list of assets to check in the specified directory...")
    assets_to_check = find_assets_to_check(args.dir)
    print(f"Found {Fore.GREEN}{len(assets_to_check)}{Style.RESET_ALL} assets to check")

    # Collect all searchable files
    print(f"\nRoot Assets directory is {Fore.GREEN}{assets_dir}{Style.RESET_ALL}")
    print(f"Extensions to check: {Fore.GREEN}{args.extensions}{Style.RESET_ALL}")
    print("Collecting list of files to search through...")
    searchable_files = collect_searchable_files(assets_dir, args.extensions)
    print(f"Found {Fore.GREEN}{len(searchable_files)}{Style.RESET_ALL} files to search through")

    # Now we actually find unused assets!
    unused_assets = []
    total_assets = len(assets_to_check)

    print(
        f"\nChecking {Fore.GREEN}{total_assets}{Style.RESET_ALL} assets for references through {Fore.GREEN}{len(searchable_files)}{Style.RESET_ALL} files..."
    )

    # Prepare arguments for parallel processing
    search_args = [(guid, searchable_files, asset_path) for guid, asset_path in assets_to_check.items()]

    # Create a process pool and run searches in parallel
    with Pool(processes=args.processes) as pool:
        with tqdm(total=total_assets, unit="assets", colour="green") as pbar:
            for result in pool.imap_unordered(find_references_to_guid, search_args):
                pbar.update(1)
                if not result[1]:
                    unused_assets.append(result[0])

    # Print results
    print(f"\n{Fore.GREEN}Analysis Complete!{Style.RESET_ALL}\n")
    if unused_assets:
        total_size = 0
        results = []

        for asset in unused_assets:
            size = os.path.getsize(asset)
            total_size += size
            rel_path = os.path.relpath(asset, assets_dir)
            results.append([rel_path, naturalsize(size)])

        # Create and print a pretty table with the results
        table = tabulate(
            results,
            headers=[f"{Fore.YELLOW}Asset Path{Style.RESET_ALL}", f"{Fore.YELLOW}Size{Style.RESET_ALL}"],
        )
        print(table)

        print(f"\n{Fore.GREEN}Summary:{Style.RESET_ALL}")
        print(
            f"- Found {Fore.RED}{len(unused_assets)}{Style.RESET_ALL} unused assets out of {Fore.GREEN}{total_assets}{Style.RESET_ALL} total assets"
        )
        print(f"- Potential savings: {Fore.RED}{naturalsize(total_size)}{Style.RESET_ALL}")

        print(
            f"\n{Fore.RED}Warning: This tool only checks for references in other Unity assets by comparing GUIDs. Do NOT blindly trust the results, as things that are not referenced in other assets but only referenced via code (classes, shaders, resources being loaded via code, etc.) WILL show up as being unused! Double check everything and make backups before deleting stuff!{Style.RESET_ALL}"
        )
    else:
        print(f"{Fore.GREEN}No unused assets found! Your project is clean!{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
