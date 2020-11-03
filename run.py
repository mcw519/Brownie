# Copyright 2020 (author: Meng Wu)

import sys
from src.user_gram import GrammarHelper, TagHelper
from src.user_ne import UserTableReader, UserCustomGraph
from src.common import load_fst, compose, union, get_result, fst_to_linear_sequence
from src.utils import int2sym

hyp_fst_path = "./sample.fst"
conf_path = "./conf"
grammar_path = conf_path + "/grammar.txt"
words_path = conf_path + "/words.txt"
phones_path = conf_path + "/phones.txt"
lex_path = conf_path + "/lexicon.txt"
user_table_path = conf_path + "/user_table.txt"
zh_syllable_path = conf_path + "/zh_syllable.txt"
jieba_lex_path = conf_path + "/jieba.lex.txt"

# load hypothesis fst
hyp_fst = load_fst(hyp_fst_path)

# create lex.fst and lex_invert.fst
creator = GrammarHelper(words_path, phones_path, jieba_lex_path) 
input_word_table = creator.word_tb # this is input sequence's symbol table
Lfst = creator.load_kaldi_lex_as_lfst(kaldi_lex=lex_path, add_disambig=False, add_position=False, add_opt_sil="SIL", invert=False)
Lfst_invert = creator.load_kaldi_lex_as_lfst(kaldi_lex=lex_path, add_disambig=False, add_position=False, add_opt_sil="SIL", invert=True)

# initial grammar helper
helperG = TagHelper(words_path, phones_path, jieba_lex_path)
fstG = helperG.read_tag_grammar(grammar_path, write_words="words_tag.txt")
fstG_subgraph = helperG.read_sub_graph_grammar(grammar_path)

# initial custom user words
helperU = UserCustomGraph(wd_table_path="words_tag.txt", phone_table_path=phones_path, zh_syllable_table_path=zh_syllable_path, \
                            jieba_lex=jieba_lex_path, user_table=user_table_path )
fstC = helperU.contextFST() # wd-in/wd-out
fstS = helperU.soundslikeFST() # ph-in/wd-out
fstI = helperU.ipaFST() # ph-in/wd-out

# this word table is the final output symbols table include the user specifically setting
user_word_table = helperU.word_table(write_words="words_user.txt")

# build graph and run
fstC = compose(Lfst, fstC) # ph-in/wd-out
user_graph = union(fstC, fstS, fstI)
all_graph = [ fstG_subgraph, Lfst_invert, user_graph ]

tag_hyp = compose(hyp_fst, fstG)
# tag_hyp.write("tag.fst")
ne_result = get_result(hyp_fst, *all_graph)
# ne_result.write("ne_result.fst")

Rfst = helperG.generate_replace_fst(ne_result, nonterminal_in="<CONTACT>", nonterminal_out="</CONTACT>", syms_tb=user_word_table)
# Rfst.write("Rfst.fst")
result = get_result(tag_hyp, Rfst)

print("input is:", int2sym(fst_to_linear_sequence(hyp_fst), syms_table=user_word_table))
print("result is:", int2sym(fst_to_linear_sequence(result), syms_table=user_word_table))

result.write("out.fst")