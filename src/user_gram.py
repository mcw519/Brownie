# Copyright 2020 (author: Meng Wu)

import pynini
import itertools
import re
from .utils import DataIO, lex_add_disambig
from .tokenizer import Tokenizer
from .common import fst_to_linear_sequence


class GrammarHelper():
    def __init__(self, words, phones, jieba_lex=None):
        # initial basic English, Punctuation and special symbol char in sigma_star, ASCII
        self.chars = [ chr(i) for i in range(1, 91) ] + [ r"\[", r"\\", r"\]" ] + [ chr(i) for i in range(94, 256) ]
        self.data_io = DataIO()
        self.word_tb = self.load_symbols(words)
        self.phone_tb = self.load_symbols(phones)
        
        # init tokenizer
        if jieba_lex is not None:
            self.tokenizer = Tokenizer(backend="jieba", jieba_dict=jieba_lex)
        else:
            self.tokenizer = Tokenizer(backend="jieba")

    def load_symbols(self, symbol_table):
        '''
            It's not a real symbol table.
            Assume symbols_tables as same form as Kaldi's words.txt and phones.txt
            Then, convert text(string) to dict's key.
        '''
        wd_syms = self.data_io.read_word_table(symbol_table)

        return wd_syms

    def pair2fst(self, x, in_syms=None, out_syms=None, weight=None):
        '''
            Input:
                x: pair with dim 1 x 2, means input/output pair
                in_syms: symbol table (dict)
                out_syms: symbol table (dict)
            Return:
                pynini.Fst object
        '''

        tokenizer = self.tokenizer

        # english split by space
        if x[0].isascii():
            _in = x[0].strip().split(" ")
        else:
            _in = tokenizer.segment(x[0]).split(" ")
        
        if x[1].isascii():
            _out = x[1].strip().split(" ")
        else:
            _out = tokenizer.segment(x[1]).split(" ")
        
        _temp = [_in, _out]
        _fst = pynini.Fst()
        if weight is not None:
            _arc_weight = pynini.Weight("tropical", weight)
        else:
            _arc_weight = pynini.Weight("tropical", 0)

        _fst.add_state() # 0-state
        cur_state = 0 # start from 0-based

        for pair in list(itertools.zip_longest(*_temp)):
            _arc_in, _arc_out = pair
            if in_syms is not None:
                try:
                    _arc_in = int(in_syms[_arc_in])
                except:
                    if _arc_in is None:
                        _arc_in = int(in_syms["<eps>"])
                    else:
                        raise ValueError("symbol not in symbol table")
        
            if out_syms is not None:
                try:
                    _arc_out = int(out_syms[_arc_out])
                except:
                    if _arc_out is None:
                        _arc_out = int(out_syms["<eps>"])
                    else:
                        raise ValueError("symbol not in symbol table")
            
            _fst.add_state()
            _fst.add_arc(cur_state, pynini.Arc(int(_arc_in), int(_arc_out), _arc_weight, cur_state + 1))
            cur_state += 1
        
        _fst.set_start(0)
        _fst.set_final(cur_state)

        return _fst

    def load_kaldi_lex_as_lfst(self, kaldi_lex, add_disambig=False, add_position=False, add_opt_sil="SIL", invert=False):
        """
            create lexicon fst with phone-in/words-out symbols
        """

        _opt_sil_state = ""

        if add_disambig:
            _lex, ndis = lex_add_disambig(kaldi_lex)
            _has_disambig = False # initial tag
        else:
            _lex = self.data_io.read_file_to_list(kaldi_lex)

        in_syms = self.phone_tb
        out_syms = self.word_tb

        _arc_weight = pynini.Weight("tropical", 0)
        _lfst = pynini.Fst()
        _lfst.add_state() # 0-state
        cur_state = 0 # start from 0-based

        for idx, line in enumerate(_lex):
            if add_disambig:
                line = line.strip().split()

            if idx == 0:
                _arc_in = int(in_syms["<eps>"])
                _arc_out = int(out_syms["<eps>"])
                _lfst.add_state()
                _lfst.add_arc(0, pynini.Arc(_arc_in, _arc_out, _arc_weight, 1))
                _lfst.set_final(1)
                cur_state = 1

            _wd = line[0] # string
            _ph_seq = line[1:] # list
            if add_position:
                if add_disambig and "#" in " ".join(_ph_seq):
                    _dis_symb = _ph_seq[-1]
                    _ph_seq = _ph_seq[:-1]
                    _has_disambig = True

                if len(_ph_seq) == 1:
                    _ph_seq = [ _ph_seq[0] + "_S" ]
                else:
                    for i, j in enumerate(_ph_seq):
                        if i == 0:
                            _ph_seq[i] = j + "_B"
                        elif i == len(_ph_seq):
                            _ph_seq[i] = j + "_E"
                        else:
                            _ph_seq[i] = j + "_I"
                
                if _has_disambig:
                    _ph_seq.append(_dis_symb)
                    _has_disambig = False

            _temp = [ _ph_seq, _wd.split(" ") ]
            for sub_idx, pair in enumerate(list(itertools.zip_longest(*_temp))):
                _arc_in, _arc_out = pair
                try:
                    _arc_in = int(in_syms[_arc_in])
                except:
                    if _arc_in is None:
                        _arc_in = int(in_syms["<eps>"])
                    else:
                        raise ValueError(_arc_in, "this symbol not in input symbol table")

                try:
                    _arc_out = int(out_syms[_arc_out])
                except:
                    if _arc_out is None:
                        _arc_out = int(out_syms["<eps>"])
                    else:
                        raise ValueError(_arc_out, "this symbol not in output symbol table")
                
                _lfst.add_state()
                if sub_idx == 0:
                    # each word start from state 1
                    _lfst.add_arc(1, pynini.Arc(_arc_in, _arc_out, _arc_weight, cur_state + 1))
                else:
                    _lfst.add_arc(cur_state, pynini.Arc(_arc_in, _arc_out, _arc_weight, cur_state + 1))
                cur_state += 1

            # return to state 1
            _arc_in = int(in_syms["<eps>"])
            _arc_out = int(out_syms["<eps>"])
            _lfst.add_arc(cur_state, pynini.Arc(_arc_in, _arc_out, _arc_weight, 1))

            if add_disambig and add_opt_sil:
                if _opt_sil_state == "":
                    _lfst.add_states(2)
                    _arc_in = int(in_syms["SIL"])
                    _arc_out = int(out_syms["<eps>"])
                    _lfst.add_arc(cur_state, pynini.Arc(_arc_in, _arc_out, _arc_weight, cur_state + 1))
                    _opt_sil_state = cur_state
                    cur_state += 1
                    _arc_in = int(in_syms["#" + str(ndis + 1)])
                    # return to state 1
                    _lfst.add_arc(cur_state, pynini.Arc(_arc_in, _arc_out, _arc_weight, 1))
                    cur_state += 1
                else:
                    _arc_in = int(in_syms["SIL"])
                    _arc_out = int(out_syms["<eps>"])
                    _lfst.add_arc(_opt_sil_state, pynini.Arc(_arc_in, _arc_out, _arc_weight, _opt_sil_state + 1))
                    _arc_in = int(in_syms["#" + str(ndis + 1)])
                    # return to state 1
                    _lfst.add_arc(_opt_sil_state + 1, pynini.Arc(_arc_in, _arc_out, _arc_weight, 1))
 
        _lfst.set_start(0)

        if invert:
            _lfst.optimize()
            _lfst.invert()
            return _lfst
        else:
            return _lfst.optimize()
    
    def load_kaldi_lex_as_lfst_reverse(self, kaldi_lex, add_disambig=False, add_position=False, add_opt_sil="SIL"):
        """
            create lexicon fst with word-in/phoneme-out symbols
            Note: optional silence still not tracking is correct or not.
        """

        _opt_sil_state = ""

        if add_disambig:
            _lex, ndis = lex_add_disambig(kaldi_lex)
            _has_disambig = False # initial tag
        else:
            _lex = self.data_io.read_file_to_list(kaldi_lex)

        in_syms = self.word_tb
        out_syms = self.phone_tb

        _arc_weight = pynini.Weight("tropical", 0)
        _lfst = pynini.Fst()
        _lfst.add_state() # 0-state
        cur_state = 0 # start from 0-based

        for idx, line in enumerate(_lex):
            if add_disambig:
                line = line.strip().split()

            if idx == 0:
                _arc_in = int(in_syms["<eps>"])
                _arc_out = int(out_syms["<eps>"])
                _lfst.add_state()
                _lfst.add_arc(0, pynini.Arc(_arc_in, _arc_out, _arc_weight, 1))
                _lfst.set_final(1)
                cur_state = 1

            _wd = line[0] # string
            _ph_seq = line[1:] # list
            if add_position:
                if add_disambig and "#" in " ".join(_ph_seq):
                    _dis_symb = _ph_seq[-1]
                    _ph_seq = _ph_seq[:-1]
                    _has_disambig = True

                if len(_ph_seq) == 1:
                    _ph_seq = [ _ph_seq[0] + "_S" ]
                else:
                    for i, j in enumerate(_ph_seq):
                        if i == 0:
                            _ph_seq[i] = j + "_B"
                        elif i == len(_ph_seq):
                            _ph_seq[i] = j + "_E"
                        else:
                            _ph_seq[i] = j + "_I"
                
                if _has_disambig:
                    _ph_seq.append(_dis_symb)
                    _has_disambig = False

            _temp = [ _wd.split(" "), _ph_seq ]
            for sub_idx, pair in enumerate(list(itertools.zip_longest(*_temp))):
                _arc_in, _arc_out = pair
                try:
                    _arc_in = int(in_syms[_arc_in])
                except:
                    if _arc_in is None:
                        _arc_in = int(in_syms["<eps>"])
                    else:
                        raise ValueError(_arc_in, "this symbol not in input symbol table")

                try:
                    _arc_out = int(out_syms[_arc_out])
                except:
                    if _arc_out is None:
                        _arc_out = int(out_syms["<eps>"])
                    else:
                        raise ValueError(_arc_out, "this symbol not in output symbol table")
                
                _lfst.add_state()
                if sub_idx == 0:
                    # each word start from state 1
                    _lfst.add_arc(1, pynini.Arc(_arc_in, _arc_out, _arc_weight, cur_state + 1))
                else:
                    _lfst.add_arc(cur_state, pynini.Arc(_arc_in, _arc_out, _arc_weight, cur_state + 1))
                cur_state += 1

            # return to state 1
            _arc_in = int(in_syms["<eps>"])
            _arc_out = int(out_syms["<eps>"])
            _lfst.add_arc(cur_state, pynini.Arc(_arc_in, _arc_out, _arc_weight, 1))

            if add_disambig and add_opt_sil:
                if _opt_sil_state == "":
                    _lfst.add_states(2)
                    _arc_in = int(in_syms["<eps>"])
                    _arc_out = int(out_syms["SIL"])
                    _lfst.add_arc(cur_state, pynini.Arc(_arc_in, _arc_out, _arc_weight, cur_state + 1))
                    _opt_sil_state = cur_state
                    cur_state += 1
                    _arc_out = int(out_syms["#" + str(ndis + 1)])
                    # return to state 1
                    _lfst.add_arc(cur_state, pynini.Arc(_arc_in, _arc_out, _arc_weight, 1))
                    cur_state += 1
                else:
                    _arc_in = int(in_syms["<eps>"])
                    _arc_out = int(out_syms["SIL"])
                    _lfst.add_arc(_opt_sil_state, pynini.Arc(_arc_in, _arc_out, _arc_weight, _opt_sil_state + 1))
                    _arc_out = int(out_syms["#" + str(ndis + 1)])
                    # return to state 1
                    _lfst.add_arc(_opt_sil_state + 1, pynini.Arc(_arc_in, _arc_out, _arc_weight, 1))
 
        _lfst.set_start(0)

        return _lfst.optimize()


class TagHelper(GrammarHelper):
    def __init__(self, words, phones, jieba_lex=None):
        super().__init__(words, phones, jieba_lex)
        self.sigma_star_fst_1state = self.gen_sigma_star_1state()
        self.sigma_star_fst_2state = self.gen_sigma_star_2state()
        self.sigma_star_fst_1state_filter = self.gen_sigma_star_1state_filter()
        self.sigma_star_fst_2state_filter = self.gen_sigma_star_2state_filter()

    def gen_sigma_star_1state(self):
        """
            one-state with self loop FST which including all words.
        """
        in_syms = self.word_tb
        out_syms = self.word_tb
        _sigma_star = pynini.Fst()
        _sigma_star.add_state() # 0-state
        _arc_weight = pynini.Weight("tropical", 0)

        for key in self.word_tb.keys():
            _arc_in = int(in_syms[key])
            _arc_out = int(out_syms[key])
            _sigma_star.add_arc(0, pynini.Arc(_arc_in, _arc_out, _arc_weight, 0))
        
        _sigma_star.set_start(0)
        _sigma_star.set_final(0)

        return _sigma_star
    
    def gen_sigma_star_2state(self):
        """
            two-states FST which including all words.
        """
        in_syms = self.word_tb
        out_syms = self.word_tb
        _sigma_star = pynini.Fst()
        _sigma_star.add_states(2) # 0 and 1 state
        _arc_weight = pynini.Weight("tropical", 0)

        for key in self.word_tb.keys():
            _arc_in = int(in_syms[key])
            _arc_out = int(out_syms[key])
            _sigma_star.add_arc(0, pynini.Arc(_arc_in, _arc_out, _arc_weight, 1))

        _sigma_star.set_start(0)
        _sigma_star.set_final(1)

        return _sigma_star
    
    def gen_sigma_star_1state_filter(self):
        """
            one-state with self loop FST which including all words.
        """
        in_syms = self.word_tb
        out_syms = self.word_tb
        _sigma_star = pynini.Fst()
        _sigma_star.add_state() # 0-state
        _arc_weight = pynini.Weight("tropical", 0)

        for key in self.word_tb.keys():
            _arc_in = int(in_syms[key])
            _arc_out = int(out_syms["<eps>"])
            _sigma_star.add_arc(0, pynini.Arc(_arc_in, _arc_out, _arc_weight, 0))
        
        _sigma_star.set_start(0)
        _sigma_star.set_final(0)

        return _sigma_star
    
    def gen_sigma_star_2state_filter(self):
        """
            two-states FST which including all words.
        """
        in_syms = self.word_tb
        out_syms = self.word_tb
        _sigma_star = pynini.Fst()
        _sigma_star.add_states(2) # 0 and 1 state
        _arc_weight = pynini.Weight("tropical", 0)

        for key in self.word_tb.keys():
            _arc_in = int(in_syms[key])
            _arc_out = int(out_syms["<eps>"])
            _sigma_star.add_arc(0, pynini.Arc(_arc_in, _arc_out, _arc_weight, 1))

        _sigma_star.set_start(0)
        _sigma_star.set_final(1)

        return _sigma_star
    
    def read_tag_grammar(self, x, write_words=None):
        """
            reading grammar file and then return grammar fst
        """
        x = self.data_io.read_file_to_list(x)
        in_syms = self.word_tb
        out_syms = self.word_tb
        _arc_weight = pynini.Weight("tropical", 0)
        _grammar_fst = pynini.Fst()

        for idx, grammar in enumerate(x):
            _gfst = pynini.Fst()
            _gfst.add_state()
            _gfst.set_start(0)
            _gfst.set_final(0)

            for i, j in enumerate(grammar):
                if j == "<SIGMA_STAR>":
                    if i != 0:
                        _gfst = _gfst + self.sigma_star_fst_2state + self.sigma_star_fst_1state
                    else:
                        _gfst = _gfst + self.sigma_star_fst_1state
                
                elif re.search("<.*>", j) and j != "<SIGMA_STAR>" and j != "<s>" and j != "</s>":
                    _temp = pynini.Fst()
                    _temp.add_states(2)
                    _arc_in = int(in_syms["<eps>"])

                    try:
                        _arc_out = int(out_syms[j])
                    except:
                        out_syms.update({j: str(len(out_syms.keys()))})
                        _arc_out = int(out_syms[j])
                    
                    _temp.add_arc(0, pynini.Arc(_arc_in, _arc_out, _arc_weight, 1))
                    _temp.set_start(0)
                    _temp.set_final(1)
                    _gfst = _gfst + _temp

                else:
                    try:
                        _arc_in = int(in_syms[j])
                        _arc_out = int(out_syms[j])
                    except:
                        raise ValueError(j, "is not in symbol tables")
                    
                    _temp = pynini.Fst()
                    _temp.add_states(2)
                    _temp.add_arc(0, pynini.Arc(_arc_in, _arc_out, _arc_weight, 1))
                    _temp.set_start(0)
                    _temp.set_final(1)
                    _gfst = _gfst + _temp

            # go back to state-0
            _arc_in = int(in_syms["<eps>"])
            _arc_out = int(out_syms["<eps>"])
            cur_state = _gfst.num_states() - 1
            _gfst.add_arc(cur_state, pynini.Arc(_arc_in, _arc_out, _arc_weight, 0))
            _gfst.set_final(0)
            _grammar_fst.union(_gfst)

        if write_words is not None:
            if not isinstance(write_words, str):
                raise(TypeError, "write_words is file path name, need a string")
            
            self.data_io.write_word_tb(out_syms, write_words)

        return _grammar_fst.optimize()
    
    def read_sub_graph_grammar(self, x):
        """
            reading grammar file and then return sub-graph grammar fst which will be used in Fst's intersection
        """
        x = self.data_io.read_file_to_list(x)
        in_syms = self.word_tb
        out_syms = self.word_tb
        _arc_weight = pynini.Weight("tropical", 0)
        _grammar_fst = pynini.Fst()

        for idx, grammar in enumerate(x):
            _gfst = pynini.Fst()
            _gfst.add_state()
            _gfst.set_start(0)
            _gfst.set_final(0)

            for i, j in enumerate(grammar):
                if j == "<SIGMA_STAR>":
                    if i != 0:
                        _gfst = _gfst + self.sigma_star_fst_2state + self.sigma_star_fst_1state
                    else:
                        _gfst = _gfst + self.sigma_star_fst_1state_filter

                elif re.search("<.*>", j) and j != "<SIGMA_STAR>" and j != "<s>" and j != "</s>":
                    _temp = pynini.Fst()
                    _temp.add_states(2)
                    _arc_in = int(in_syms["<eps>"])
                    # no show <tag> in sub-graph
                    _arc_out = int(out_syms["<eps>"])
                    
                    # # show <tag> in sub-graph
                    # try:
                    #     _arc_out = int(out_syms[j])
                    # except:
                    #     out_syms.update({j: str(len(out_syms.keys()))})
                    #     _arc_out = int(out_syms[j])
                    
                    _temp.add_arc(0, pynini.Arc(_arc_in, _arc_out, _arc_weight, 1))
                    _temp.set_start(0)
                    _temp.set_final(1)
                    _gfst = _gfst + _temp
                
                else:
                    try:
                        _arc_in = int(in_syms[j])
                        _arc_out = int(out_syms["<eps>"])
                    except:
                        raise ValueError(j, "is not in symbol tables")
                    
                    _temp = pynini.Fst()
                    _temp.add_states(2)
                    _temp.add_arc(0, pynini.Arc(_arc_in, _arc_out, _arc_weight, 1))
                    _temp.set_start(0)
                    _temp.set_final(1)
                    _gfst = _gfst + _temp

            # go back to state-0
            _arc_in = int(in_syms["<eps>"])
            _arc_out = int(out_syms["<eps>"])
            cur_state = _gfst.num_states() - 1
            _gfst.add_arc(cur_state, pynini.Arc(_arc_in, _arc_out, _arc_weight, 0))
            _gfst.set_final(0)
            _grammar_fst.union(_gfst)

        return _grammar_fst.optimize()
    
    def generate_replace_fst(self, fst_in, nonterminal_in, nonterminal_out, syms_tb):
        _arc_weight = pynini.Weight("tropical", 0)

        fst_in_seq = fst_to_linear_sequence(fst_in)
        ne_fst = pynini.Fst()
        ne_fst.add_state()
        ne_fst.set_start(0)
        ne_fst.set_final(0)

        for i in fst_in_seq.split():
            _fst = self.pair2fst(["0", i])
            ne_fst = ne_fst + _fst
        ne_fst.optimize()

        terminal_in_fst = pynini.Fst()
        terminal_in_fst.add_states(2)
        _arc_in = int(syms_tb[nonterminal_in])
        _arc_out = int(syms_tb["<eps>"])
        terminal_in_fst.add_arc(0, pynini.Arc(_arc_in, _arc_out, _arc_weight, 1))
        terminal_in_fst.set_start(0)
        terminal_in_fst.set_final(1)

        terminal_out_fst = pynini.Fst()
        terminal_out_fst.add_states(2)
        _arc_in = int(syms_tb[nonterminal_out])
        _arc_out = int(syms_tb["<eps>"])
        terminal_out_fst.add_arc(0, pynini.Arc(_arc_in, _arc_out, _arc_weight, 1))
        terminal_out_fst.set_start(0)
        terminal_out_fst.set_final(1)

        replace_fst = self.sigma_star_fst_1state + terminal_in_fst + self.sigma_star_fst_2state_filter + self.sigma_star_fst_1state_filter + ne_fst + terminal_out_fst + self.sigma_star_fst_1state

        return replace_fst
