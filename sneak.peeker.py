#!/usr/bin/env python

import sys
import argparse
import os
import yaml
import re
import nltk
import operator

# Global variables
prog = os.path.basename(__file__)
prog_dir = ".snk"
test_prefix = "test__"


def main():
  # Top level parser
  parser = argparse.ArgumentParser()
  parser.add_argument(
      "-d",
      "--directory",
      metavar="DIR",
      help="directory to save program files",
      default=prog_dir)
  parser.add_argument(
      "-v", "--verbose", action="store_true", help="show additional output")
  subparsers = parser.add_subparsers(
      title='subcommands', description='valid subcommands')

  # Parser for init
  parser_init = subparsers.add_parser(
      "init", help="initializes the current directory")
  parser_init.set_defaults(func=init)

  # Parser for add
  parser_add = subparsers.add_parser(
      "add", help="adds test files to the staging area")
  parser_add.add_argument(
      "tests", metavar="FILE", help="test file to add", nargs='+')
  parser_add.set_defaults(func=add)

  # Parser for commit
  parser_commit = subparsers.add_parser(
      "commit", help="splits staged test files by question")
  parser_commit.set_defaults(func=commit)

  # Parser for push
  parser_push = subparsers.add_parser(
      "push", help="parses given sneak peek for all staged questions")
  parser_push.add_argument("sneak", metavar="FILE", help="sneak peek file to process")
  parser_push.set_defaults(func=push)

  # Main
  args = parser.parse_args()
  if args.verbose: print "%s ran with verbose output" % prog
  args.directory = os.path.abspath(args.directory)
  if args.verbose: print "%s directory: %s" % (prog, args.directory)
  args.func(args)


def assert_directory(directory):
  if not os.path.isdir(directory):
    sys.exit("fatal: not a directory: %s" % (prog, directory))


def sneak_peek(string):
  string_lower = string.lower()
  string_stripped = re.sub("[^A-Za-z0-9]", "\n", string_lower)
  string_split = string_stripped.split()
  string_unique = set(string_split)
  return sorted(string_unique)


# Some methods I thought I would use - andgates

def get_bow(tagged_tokens, stopwords):
    return set([t[0].lower() for t in tagged_tokens if t[0].lower() not in stopwords])

# The standard NLTK pipeline for POS tagging a document
def get_sentences(text):
    sentences = nltk.sent_tokenize(text)
    sentences = [nltk.word_tokenize(sent) for sent in sentences]
    sentences = [nltk.pos_tag(sent) for sent in sentences]

    return sentences

# qbow: is a list of pos tagged question tokens with SW removed
# sentences: is a list of pos tagged story sentences
# stopwords is a set of stopwords
def baseline(qbow, sentences, stopwords):
    
    # Collect all the candidate answers
    answers = []
    for sent in sentences:
        # A list of all the word tokens in the sentence
        sbow = get_bow(sent, stopwords)
        
        # Count the # of overlapping words between the Q and the A
        # & is the set intersection operator
        overlap = len(qbow & sbow)
        
        answers.append((overlap, sent))
        
    # Sort the results by the first element of the tuple (i.e., the count)
    # Sort answers from smallest to largest by default, so reverse it
    answers = sorted(answers, key=operator.itemgetter(0), reverse=True)

    # Return the best answer
    #best_answer = (answers[0])[1]    
    return answers


def find_common_chunks(test_text, peek_text):

  stopwords = set(nltk.corpus.stopwords.words("english"))

  qbow = get_bow(get_sentences(peek_text)[0], stopwords)
  sentences = get_sentences(test_text)
  answers = baseline(qbow, sentences, stopwords)

  ans = []

  for idx,item in answers:
    ans.append((idx, " ".join(t[0] for t in item)))

  return ans

# End of some methods I thought I would use - andgates

def init(args):
  if os.path.isdir(args.directory):
    exit("Existing %s directory: %s" % (prog, args.directory))
  os.makedirs(args.directory)
  print "Initialized empty %s directory: %s" % (prog, args.directory)


def add(args):
  assert_directory(args.directory)
  all_results = []
  for test in args.tests:
    # TODO: Handle UNIX file expressions, wildcards, etc
    test_infile = os.path.abspath(test)
    test_name = os.path.basename(test_infile)
    test_object = None
    test_outfile = args.directory + "/" + test_name + ".yaml"
    if not os.path.isfile(test_infile):
      print "warning: test %s cannot be found, ignoring: %s" % (test_name,
          test_infile)
    elif os.path.exists(test_outfile):
      print "warning: test %s is already added, ignoring: %s" % (test_name,
          test_outfile)
    else:
      print "%s is a valid file: %s -> %s" % (test, test_infile, test_outfile)
      test_infile_object = open(test_infile, "r")
      test_outfile_object = open(test_outfile, "w")
      test_infile_contents = test_infile_object.read()
      test_outfile_dict = dict(
          dictionary=sneak_peek(test_infile_contents),
          name=test_name,
          path=test_infile,
          text=test_infile_contents.splitlines())

      test_outfile_object.write(yaml.dump(test_outfile_dict))
      test_infile_object.close()
      test_outfile_object.close()


      # Begin messy code added by andgates

      test_text = test_infile_contents.splitlines()
      peek_text = sneak_peek(test_infile_contents)


      peek_file = open("final_sneak_peek.txt", "r")
      peek_file_contents = peek_file.read()
      peek_file_text = peek_file_contents.splitlines()
      peek_file.close()


      # Do some craziness to parse the questions
      question = []
      partial = []
      q_string = ""
      qs = []
      current_question = None
      for line in test_text:
        m = re.search('(\d\.) \w', line)
        if "Multiple choice" in line:
          current_question = None
        elif m:
          question.append(partial)
          for p in partial:
            q_string += p + " "
          qs.append(q_string)
          partial = []
          current_question = m.groups()
          partial.append(line)
        elif current_question:
          partial.append(line)


      # Load the current sneak.peek
      peek_list_full = nltk.word_tokenize(peek_file_contents)

      stopwords = set(nltk.corpus.stopwords.words("english"))

      peek_list = [w for w in peek_list_full if w not in stopwords]

      results = []

      # Find the overlap
      for q in question:
        overlapcount = 0
        q_string = " "
        #print "Question:"
        for line in q:
          q_string += line + " "
          #print line
        q_list = nltk.word_tokenize(q_string)
        overlap = set(q_list).intersection(set(peek_list))
        overlapcount += len(overlap)
        #print "Overlapped: %s" % overlap
        #print "Overlap: %s \n\n" % overlapcount
        results.append((overlapcount, overlap, q))
        all_results.append((overlapcount, overlap, q, test_name))

      # Sort the results
      sresults = sorted(results, key=operator.itemgetter(0), reverse=True)

      test_outfile = args.directory + "/" + test_name + ".out"
      test_outfile_object = open(test_outfile, "w")

      # Write to file
      for r in sresults:
        test_outfile_object.write("Question:\n")
        for line in r[2]:
            q_string += line + " "
            test_outfile_object.write(line)
            test_outfile_object.write("\n")

        test_outfile_object.write("Overlapped: %s \n" % r[1])
        test_outfile_object.write("Overlap: %s \n\n" % r[0])


      test_outfile_object.close()

    pass

    test_outfile = args.directory + "/" + "all_results" + ".out"
    test_outfile_object = open(test_outfile, "w")

    all_sresults = sorted(all_results, key=operator.itemgetter(0), reverse=True)

    # Write all results to file
    for r in all_sresults:
      test_outfile_object.write("Test: %s\n" % r[3])
      test_outfile_object.write("Question:\n")
      for line in r[2]:
          q_string += line + " "
          test_outfile_object.write(line)
          test_outfile_object.write("\n")

      test_outfile_object.write("Overlapped: %s \n" % r[1])
      test_outfile_object.write("Overlap: %s \n\n" % r[0])


    test_outfile_object.close()

    # End messy code added by andgates

  pass

def commit(args):
  # Not implimented. Should adapt code added by andgates in add method
  assert_directory(args.directory)

def push(args):
  # Not implimented
  assert_directory(args.directory)


if __name__ == "__main__":
  main()
