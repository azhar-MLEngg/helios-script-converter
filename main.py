#!/usr/bin/env python3
import asyncio
import logging
import sys

from helios_converter.agent import run_conversion

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

if __name__ == "__main__":
    zip_path = sys.argv[1] if len(sys.argv) > 1 else "input_files.zip"
    output_folder = sys.argv[2] if len(sys.argv) > 2 else "output_files"
    asyncio.run(run_conversion(zip_path=zip_path, output_folder=output_folder))
