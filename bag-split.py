#!/usr/bin/env python
"""
BagIt Splitting and Unsplitting Tools
by Stephen Eisenhauer

This tool has two modes:

 * splitcheck

   Run after using the BagIt Library's split operation to perform integrity
   checks and to preserve the original bag's metadata along with the split bags

   Command-line usage:
      % python bag-split.py splitcheck /path/to/bag

   API USage:
      result = verify_split("/original/bag/directory", bags_dir=None, no_verify=False)
      result is a value of True or False

 * unsplit

   Run against a directory containing split bags to reconstruct (unsplit) a
   copy of the original bag

   API Usage:
      bag = unsplit("/parent/dir/of/bags")

   Command-line usage:
      % python bag-split.py unsplit /parent/dir/of/bags
"""
import argparse
import sys
import os
import bagit
import shutil
import re


def make_metadata_bag(bag_dir, bags_dir=None):
    """
    Store the bag's metadata files in a new bag alongside split bags
    """
    if bags_dir == None:
        bags_dir = bag_dir + "_split"

    # Bag directories better be valid or somebody's getting stabbed
    if not os.path.isdir(bag_dir):
        raise RuntimeError("no such bag directory %s" % bags_dir)
    if not os.path.isdir(bags_dir):
        os.makedirs(bags_dir)
    if not os.path.isdir(bags_dir):
        raise RuntimeError("no such bags directory %s" % bags_dir)

    # Get bag directory name (by itself)
    bag_name = os.path.basename(os.path.abspath(bag_dir))

    # Set up our new metadata bag directory
    meta_bag_name = bag_name + "__metadata"
    meta_bag_path = os.path.join(bags_dir, meta_bag_name)
    if os.path.isdir(meta_bag_path):
        print "Metadata bag already exists. To regenerate it, remove it and " \
              "then try again."
        return False
    print "Creating metadata bag: %s" % meta_bag_name
    os.makedirs(meta_bag_path)

    # Copy the bag's metadata files to the new metadata bag directory
    for f in os.listdir(bag_dir):
        print "Found file: " + f
        if f == 'data':
            pass
        elif os.path.isdir(f):
            shutil.copytree(f, meta_bag_path, True)
        else:
            shutil.copy2(os.path.join(bag_dir, f), meta_bag_path)

    # Bag up the metadata
    meta_bag = bagit.make_bag(meta_bag_path)

    return meta_bag

def compare_payloads(new_entries, original_entries):
    """
    Where new_entries and original_entries are the entry format
    returned by bagit.Bag, return true if all of the payload
    entries match
    """

    match = True
    missing_entries = {}

    new_entries_payload_keys = []
    original_entries_payload_keys = []

    for key in new_entries.keys():
        if key.startswith("data/"):
            new_entries_payload_keys.append(key)

    for key in original_entries.keys():
        if key.startswith("data/"):
            original_entries_payload_keys.append(key)
    
    for key in new_entries_payload_keys:
       if key not in original_entries_payload_keys:
           match = False
           break
       if new_entries[key] != original_entries[key]:
           match = False
           break

    diff_set = set(original_entries_payload_keys) - set(new_entries_payload_keys)

    for key in diff_set:
        missing_entries[key] = original_entries[key]

    return (match, missing_entries)


def verify_split(bag_dir, bags_dir=None, no_verify=False):
    """
    Verify that a bag split went okay.
    """
    errors = False

    if bags_dir == None:
        bags_dir = bag_dir + "_split"

    if not os.path.isdir(bag_dir):
        raise RuntimeError("no such bag directory %s" % bag_dir)

    if not os.path.isdir(bags_dir):
        raise RuntimeError("no such bags directory %s" % bags_dir)

    # Let's get set up
    os.chdir(bags_dir)
    bags = []               # Bag objects will go in here
    all_entries = dict()    # Manifest entries will get collected in here

    # Collect all the split Bag objects we wish to check
    for f in os.listdir('.'):
        if os.path.isdir(os.path.join(bags_dir, f)):
            bag = bagit.Bag(f)
            if no_verify:
                print "Skipping verification for bag %s" % f
                all_entries.update(bag.entries)
            else:
                print "Verifying bag %s..." % f,
                if bag.validate():
                    #bags.append(bag)
                    if not f.endswith("__metadata"):
                        #Don't add the entries from the metadata bag, since these aren't part
                        #of the original payload
                        all_entries.update(bag.entries)
                    print "success."
                else:
                    print "failed!"
                    errors = True
    #bags.sort(key=lambda bag: bag.path)

    # Start looking at the original (pre-split) Bag
    original_bag = bagit.Bag(bag_dir)
    if no_verify:
        "Not verifying original bag at user's request."
    else:
        print "Verifying original bag integrity...",
        if original_bag.validate():
            print "success."
        else:
            print "failed!"
            errors = True

    # Compare sums to accumulated sub-bag sums
    #if original_bag.entries == all_entries:
    result = compare_payloads(all_entries, original_bag.entries)
    if result[0] == True:
        print "Original manifest entries appear to be identical to the split " \
              "manifests' entries."
    else:
        print "Original manifest does NOT appear consistent with the split " \
              "manifests! Diff:"
        diff = set(original_bag.entries) - set(all_entries)
        print diff
        diff = set(all_entries) - set(original_bag.entries)
        print diff
        errors = True

    if len(result[1]):
        print "Warning: The following entries are present in the original bag, but not in the split bags:"
        print result[1]

    return not errors


def unsplit(bags_dir, merged_path=False, no_verify=False):
    """
    Unsplit (merge) the bags in a given directory.
    """
    if not os.path.isdir(bags_dir):
        raise RuntimeError("no such bags directory %s" % bags_dir)

    # Let's get set up
    working_dir = os.getcwd()
    os.chdir(bags_dir)
    bags = []               # Bag objects will go in here
    all_entries = dict()    # Manifest entries will get collected in here
    meta_bag_path = False

    # Collect all the Bag objects we wish to merge
    for f in os.listdir(bags_dir):
        # If f is a directory
        if os.path.isdir(os.path.join(bags_dir, f)):
            # If f appears to be a metadata bag
            if re.match(".*__metadata$", f):
                meta_bag_path = os.path.join(bags_dir, f)
            else:
                #Anything not a metadata bag is considered a valid sub-bag. We're not
                #enforcing it to be numerical, since this won't apply for bags split
                #by filetype
                bag = bagit.Bag(f)

                if no_verify:
                    verified = True
                    print "Skipping verification for bag %s." % f
                else:
                    print "Validating bag %s..." % f,
                    verified = bag.validate()

                if verified:
                    all_entries.update(bag.entries)
                    bag.common_info = bag.info
                    bag.common_info.pop("Payload-Oxum", None)
                    bag.common_info.pop("Bag-Size", None)
                    bag.common_info.pop("Bag-Count", None)
                    bag.common_info.pop("Bagging-Date", None)
                    bag.common_info.pop("File-Type", None) #Needed for when bags are split by filetype
                    bags.append(bag)
                    print "success."
                else:
                    print "failed!"

    if len(bags) < 1: #did we find any sub-bags in the directory?
        raise RuntimeError("No split-bags found to join in path %s" % bag_dir)
    bags.sort(key=lambda bag: bag.path)

    # Sanity Check
    # Make sure there are no contradictions between bag-info tags in all bags
    common_info = bags[0].common_info
    for bag in bags:
        if bag.common_info != common_info:
            print "Metadata from %s does not match the first bag..." % bag.path
            print "First bag (%s) metadata:" % bags[0].path
            print common_info
            print "Bag %s metadata:" % bag.path
            print bag.common_info
            raise RuntimeError("bag metadata mismatch in bag: %s" % bag.path)

    # Come up with a name for the merged bag folder
    if merged_path:
        merged_path = os.path.abspath(os.path.join(working_dir, merged_path))
    else:
        path, bags_dir_name = os.path.split(bags_dir)
        match = re.match("(.*)_split$", bags_dir_name)
        if match:
            merged_name = match.group(1)
        else:
            merged_name = "%s_merged" % bags_dir_name
        merged_path = os.path.join(bags_dir, '..', merged_name)
    merged_path = os.path.abspath(merged_path)  # Clean up /../ instances

    # Make sure the path isn't already taken, then create the folder
    if os.path.isdir(merged_path):
        raise RuntimeError("destination directory exists: %s" % merged_path)
    os.mkdir(merged_path)

    # Copy payloads from bags into merged bag payload
    for bag in bags:
        print "Copying payload from %s..." % bag.path
        mergetree(os.path.join(bag.path, "data"), merged_path)

    # Turn the merged payload into a bag
    merged_bag = bagit.make_bag(merged_path, common_info)

    # Compare sums to accumulated sub-bag sums
    #if merged_bag.entries == all_entries
    result = compare_payloads(merged_bag.entries, all_entries)
    if result[0] == True:
        print "New manifest entries appear to be identical to the split " \
              "manifests' entries."
    else:
        print "New manifest does NOT appear consistent with the split " \
              "manifests!"
        raise RuntimeError("merged bag manifest inconsistent with split " \
                           "manifests")

    # If _metadata bag is present, unpack it in merged bag's root
    if (meta_bag_path):
        meta_bag = bagit.Bag(meta_bag_path)
        if not meta_bag.validate():
            print "The metadata bag failed to validate!"
            raise RuntimeError("metadata bag failed validation")
        # TODO: Unpack bag contents into merged_path
        print "Copying metadata bag payload to merged bag"
        mergetree(os.path.join(meta_bag.path, "data"), merged_path)

        # Since we messed with the bag's metadata, let's reload and verify it
        # before we finish
        merged_bag = bagit.Bag(merged_path)
        if no_verify:
            print "Skipping merged bag validation at user's request."
        else:
            if merged_bag.validate():
                print "The final merged bag validated successfully."
            else:
                print "The final merged bag failed to validate!"
                raise RuntimeError("merged bag failed validation")

    print "The merged bag was written to: %s" % merged_path

    return merged_bag


def mergetree(src, dst, symlinks=False, ignore=None):
    """
    Adaptation of shutil.copytree() that allows for merging existing dirs.
    """
    names = os.listdir(src)
    if ignore is not None:
        ignored_names = ignore(src, names)
    else:
        ignored_names = set()

    # Suppress "file exists" error
    try:
        os.makedirs(dst)
    except OSError:
        # do nothing
        # TODO: Raise exception if the OSError isn't a "file exists" error
        pass

    errors = []
    for name in names:
        if name in ignored_names:
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                mergetree(srcname, dstname, symlinks, ignore)
            else:
                shutil.copy2(srcname, dstname)
            # XXX What about devices, sockets etc.?
        except (IOError, os.error) as why:
            errors.append((srcname, dstname, str(why)))
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except shutil.Error as err:
            errors.extend(err.args[0])
    try:
        shutil.copystat(src, dst)
    except WindowsError:
        # can't copy file access times on Windows
        pass
    except OSError as why:
        errors.extend((src, dst, str(why)))
    if errors:
        raise shutil.Error(errors)


def _make_arg_parser():
    parser = argparse.ArgumentParser(
        description='Tools for splitting/unsplitting BagIt bags.')
    parser.add_argument('operation', choices=['splitcheck', 'unsplit'],
        help="selects which operation to perform")
    parser.add_argument('bag',
        help="path to the bag being split (or parent of bags being unsplit)")
    parser.add_argument('--no-verify', action="store_true",
        help="skips checksum validation (not recommended)")
    parser.add_argument('-o', '--output-dir',
        help="directory name to use for the merged bag (when unsplitting). " \
             "(relative to working directory)"
    )

    return parser


if __name__ == "__main__":
    parser = _make_arg_parser()
    args = parser.parse_args()
    bag_path = os.path.abspath(args.bag)

    if args.operation == "splitcheck":
        try:
            result = verify_split(bag_path, None, args.no_verify)
            if result:
                make_metadata_bag(bag_path)
        except Exception, e:
            print "An error has occurred: %s" % e
            sys.exit(1)

    elif args.operation == "unsplit":
        try:
            unsplit(bag_path, args.output_dir, args.no_verify)
        except Exception, e:
            print "An error has occurred: %s" % e
            sys.exit(1)
