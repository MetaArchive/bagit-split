#!/bin/bash
#
# findbadfiles.sh
#
# Prints out paths of files which are either unwanted or whose filenames
# contain characters that could become problematic after LOCKSS ingests later
# on.
# 
# This includes files such as:
#  .DS_Store
#  Thumbs.db
#  Filenames beginning with a dot or other punctuation
#  Filenames containing spaces and other non-URL-safe characters (also tildes)
# 
# See the code for the full list of patterns searched.
#
# Usage:
#     ./findbadfiles.sh <DIR>

DIR=$1

if [ "$DIR" == "" ]; then
    echo "Usage: findbadfiles.sh <DIR>"
    exit 1
fi

# Files named Thumbs.db
find $DIR -iname "Thumbs.db"

# Names with leading punctuation (including .DS_Store)
find $DIR -name ".*"
find $DIR -name "_*"
find $DIR -name "-*"

# Files with non-URL-safe chars or tildes (which are URL-safe, but gross)
find $DIR -not -iregex "[a-z0-9\.\_/-]+"
