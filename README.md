# BagIt Splitting and Unsplitting Tools

## Overview

This tool provides functionality for splitting BagIt bags into a collection of
smaller bags, and for "unsplitting" these bags back into a single bag mostly
identical to the original.

## Usage

To see the full command-line help text, do:

    $ python bag-split.py --help

### Splitting a Bag

    $ bag splitbagbysize <BAG> --maxbagsize 30
    $ python bag-split.py split <BAG>

The first command above uses the official BagIt command-line utility
(`bag`) to split the original <BAG>, in this example using 30GB as the
per-bag limit.

The second command uses this tool to verify the split bags against the
original bag for integrity and completeness, as well as to create an
additional "metadata" bag among the split bags (which preserves the
state of the original bag's metadata).

### Unsplitting a Bag

    $ python bag-split.py unsplit <DIRECTORY CONTAINING BAGS>

This command creates a new directory called `MERGED_BAG` by merging the
bags found inside <DIRECTORY CONTAINING BAGS> into a single reconstructed
bag.  The tool will check that the reconstructed bag is a faithful
reconstruction of the original.

## License

See LICENSE.txt
