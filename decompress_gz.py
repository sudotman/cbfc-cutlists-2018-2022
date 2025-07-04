import gzip
import shutil
from pathlib import Path


def decompress_gz_files(root: Path = Path('.')) -> None:
    """Walk *root* recursively, decompressing every .gz file found.

    If the destination (filename without .gz) already exists, it will be left
    untouched. A small progress message is printed for each file handled.
    """
    for gz_path in root.rglob('*.gz'):
        dest_path = gz_path.with_suffix('')  # strip one suffix (.gz)
        if dest_path.exists():
            print(f'Skip (exists): {dest_path}')
            continue

        try:
            with gzip.open(gz_path, 'rb') as f_in, open(dest_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
            print(f'Decompressed: {gz_path} -> {dest_path}')
        except Exception as exc:
            print(f'Error decompressing {gz_path}: {exc}')


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Decompress all .gz files in a directory tree.')
    parser.add_argument('path', nargs='?', default='.', help='Root directory to scan (default: current directory)')
    args = parser.parse_args()

    decompress_gz_files(Path(args.path).expanduser().resolve())


if __name__ == '__main__':
    main() 