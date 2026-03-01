#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Convert local file paths to file:// URLs for use with AI image reading tools.

This script handles:
- Unix paths (/home/user/image.jpg)
- Windows paths (C:\Users\name\image.png)
- Relative paths (./image.jpg, ../photos/pic.png)

Usage:
    python path_to_url.py "/path/to/image.jpg"
    python path_to_url.py "C:\Users\name\Pictures\photo.png"
    python path_to_url.py "./relative/path/image.gif"

Output:
    file:///absolute/path/to/image.jpg
"""

import sys
import os
import urllib.parse
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def path_to_url(path_str: str) -> str:
    """
    Convert a file path to a file:// URL.
    
    Args:
        path_str: Local file path (absolute or relative)
        
    Returns:
        file:// URL string
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the path is invalid
    """
    # Strip quotes if present
    path_str = path_str.strip('"\'')
    
    # Expand user home directory (~)
    path_str = os.path.expanduser(path_str)
    
    # Convert to Path object
    path = Path(path_str)
    
    # Resolve to absolute path
    try:
        abs_path = path.resolve(strict=True)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path_str}")
    except Exception as e:
        raise ValueError(f"Invalid path '{path_str}': {e}")
    
    # Convert to file:// URL
    # On Windows, Path.as_posix() converts backslashes to forward slashes
    posix_path = abs_path.as_posix()
    
    # URL encode the path to handle special characters
    encoded_path = urllib.parse.quote(posix_path, safe='/')
    
    # Build the file:// URL
    # On Windows, path starts with drive letter (e.g., C:), needs leading /
    # On Unix, path already starts with /
    if posix_path.startswith('/'):
        url = f"file://{encoded_path}"
    else:
        # Windows path without leading / (shouldn't happen with resolve())
        url = f"file:///{encoded_path}"
    
    return url


def main():
    if len(sys.argv) < 2:
        print("Usage: python path_to_url.py <file_path>", file=sys.stderr)
        print('Example: python path_to_url.py "C:\\Users\\name\\image.jpg"', file=sys.stderr)
        sys.exit(1)
    
    # Join all arguments to handle paths with spaces
    path_input = ' '.join(sys.argv[1:])
    
    # On Windows, use os.path.abspath instead of Path.resolve() to avoid encoding issues
    # with Chinese characters in console environment
    if os.name == 'nt':
        try:
            # Expand user home and get absolute path
            expanded = os.path.expanduser(path_input.strip('"\''))
            abs_path = os.path.abspath(expanded)
            if not os.path.exists(abs_path):
                raise FileNotFoundError(f"File not found: {path_input}")
            # Convert to forward slashes and create file:// URL
            posix_path = abs_path.replace('\\', '/')
            encoded_path = urllib.parse.quote(posix_path, safe='/')
            url = f"file:///{encoded_path}"
            print(url)
            return
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(2)
        except Exception as e:
            print(f"Error: Invalid path '{path_input}': {e}", file=sys.stderr)
            sys.exit(3)
    
    # Unix/Linux/Mac - use original Path-based approach
    try:
        url = path_to_url(path_input)
        print(url)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(4)


if __name__ == "__main__":
    main()
