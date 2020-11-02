# Copyright 2020 (author: Meng Wu)

import io
from .utils import DataIO, make_context_fst, update_wd_table
from .tokenizer import Tokenizer
import pynini
from .common import list2fst


class UserTableReader(DataIO):
    def __init__(self, encode="utf-8", split_space=" ", wd_table_path="test_data/words.txt", \
                    phone_table_path="test_data/phones.txt", zh_syllable_table_path="test_data/zh_syllable.txt"):
        super().__init__(encode="utf-8", split_space=" ")

        self.wd_table = self.read_word_table(wd_table_path)
        self.phone_table = self.read_word_table(phone_table_path)
        self.zh_syllable_table = self.read_zh_syllable_table(zh_syllable_table_path)

    def read_zh_syllable_table(self, x):
        dct = {}
        with io.open(x, "r", encoding=self.encode) as f:
            for line in f.readlines():
                line = line.strip().split()
                syllable = line[0]
                phones = " ".join(line[1:])
                dct.update({syllable: phones})
        
        return dct
    
    def is_oov(self, wd, check_type="word"):
        """
            Read a word and check it is oov or not.
            Input:
                wd: string
                check_type: "word" or "syllable" check
            Retrun:
                True/False
        """
        wd_table = self.wd_table
        zh_syllable_table = self.zh_syllable_table

        try:
            if check_type == "word":
                _ = wd_table[wd]
            elif check_type == "syllable":
                _ = zh_syllable_table[wd]
            return False

        except KeyError:
            return True

    def read_user_table(self, x):
        """
            Read user table
            Input:
                x: string, user_tb path
            Return:
                dct: user table stored in dict
                new_word_table
        """
        dct = {}
        oov_list = []
        with io.open(x, "r", encoding=self.encode) as f:
            user_table = [ i.strip().split(",") for i in f ]

        for idx, content in enumerate(user_table):

            # check column key as:
            if idx == 0:
                for kid, j in enumerate(content):
                    if j == "Phrase":
                        phrase_key = kid
                    elif j == "SoundsLike":
                        soundslike_key = kid
                    elif j == "IPA":
                        ipa_key = kid
                    elif j == "DisplayAs":
                        displayas_key = kid
                
            else:
                if content[phrase_key] == "":
                    raise TypeError("Phrase must be given." + " " + "line " + str(idx+1) + " " + ",".join(content))
                else:
                    if content[soundslike_key] != "":
                        for _, syllable in enumerate(content[soundslike_key].split("-")):
                            # check syllable is legal
                            if self.is_oov(syllable, check_type="syllable"):
                                raise TypeError("illagle syllables in SoundsLike." + " " + "line " + str(idx+1) + " " + ",".join(content))
                
                    if content[displayas_key] == "":
                        # if DisplayAs is empty, using Phrase to replace.
                        # Equal to defined specific hotwords.
                        content[displayas_key] = content[phrase_key]

                    dct[content[phrase_key]] = {"SoundsLike": content[soundslike_key], "IPA": content[ipa_key], "DisplayAs": content[displayas_key]}
                    if self.is_oov(content[displayas_key], check_type="word"):
                        oov_list.append(content[displayas_key])

        return dct, oov_list


class UserCustomGraph(UserTableReader):
    def __init__(self, user_table, wd_table_path, phone_table_path, zh_syllable_table_path, \
                    jieba_lex=None, encode="utf-8", split_space=" "):
        """
            wd_table must be as same as decoding graph used.
            Args:
                user_dct(dict): dct[phrase] = {"SoundsLike": xxx,"IPA": xxx, "DisplayAs": xxx}
                wd_table(dict): {wd1: int, wd2: int, etc.}
        """
        super().__init__(encode=encode, split_space=split_space, wd_table_path=wd_table_path, \
            phone_table_path=phone_table_path, zh_syllable_table_path=zh_syllable_table_path)

        self.user_dct, self.oov_list = self.read_user_table(user_table)

        if jieba_lex is not None:
            self.tokenizer = Tokenizer(backend="jieba", jieba_dict=jieba_lex) ## need a Jieba dictionay
        else:
            self.tokenizer = Tokenizer(backend="jieba")

    def contextFST(self):
        return self.get_contextFST()
    
    def soundslikeFST(self):
        return self.get_soundslikeFST()
    
    def ipaFST(self):
        return self.get_ipaFST()
    
    def word_table(self, write_words=None):
        new_words_table = update_wd_table(self.wd_table, self.oov_list)
        
        if write_words is not None:
            if not isinstance(write_words, str):
                raise(TypeError, "write_words is file path name, need a string")
            
            self.write_word_tb(new_words_table, write_words)

        return new_words_table

    def get_contextFST(self, hot_weight=0.9, non_hot_weight=0.1):
        """
            as same as building context C.fst.txt
            Fst type:
                word-in / word-out
            Return:
                C: list, will be called by _get_contextFST()
        """
        user_dct = self.user_dct
        wd_table = self.wd_table
        context_lex_form = []

        # working on user-hotword.
        for _, phrase in enumerate(user_dct.keys()):
            if user_dct[phrase]["DisplayAs"] != "":
                try:
                    wd_table[phrase]
                    phrase_inside = phrase
                except:
                    phrase_inside = self.tokenizer.segment(phrase)
                _c = " ".join([user_dct[phrase]["DisplayAs"], str(hot_weight), phrase_inside])
                context_lex_form.append(_c.split())
        
        # working on non-hotword.
        for _, wd in enumerate(wd_table.keys()):
            # avoid epsilon symbols in WFST.
            if wd != "<eps>":
                if wd not in user_dct.keys():
                    _c = " ".join([wd, str(non_hot_weight), wd])
                    context_lex_form.append(_c.split())
        
        return list2fst(make_context_fst(context_lex_form), self.word_table(), self.word_table())
    
    def get_soundslikeFST(self):
        """
            build like lexicon.txt, but used non-position dependent phones and no pronunciation weight
            Fst type:
                phone-in / word-out
            Return:
                P: list, will be called by _get_contextFST()
        """
        user_dct = self.user_dct
        zh_syllable_table = self.zh_syllable_table
        soundslike_lex = []
        fake_weight = 0.
        for _, phrase in enumerate(user_dct.keys()):
            if user_dct[phrase]["SoundsLike"] != "":
                try:
                    syllable_list = user_dct[phrase]["SoundsLike"].split("-")
                    phone_seq = ""
                    for j in syllable_list:
                        phone_seq += zh_syllable_table[j]
                        phone_seq += " "
                        _c = " ".join([user_dct[phrase]["DisplayAs"], str(fake_weight), phone_seq])                   

                except:
                    continue
                
                soundslike_lex.append(_c.split())

        return list2fst(make_context_fst(soundslike_lex, weight=False), self.phone_table, self.word_table())

    def get_ipaFST(self):
        """
            build like lexicon.txt, but used non-position dependent phones and no pronunciation weight
            Fst type:
                phone-in / word-out
            Return:
                P: list, will be called by _get_contextFST()
        """
        user_dct = self.user_dct
        phone_dct = self.phone_table
        ipa_lex = []
        fake_weight = 0.
        for _, phrase in enumerate(user_dct.keys()):
            if user_dct[phrase]["IPA"] != "":
                ipa_list = user_dct[phrase]["IPA"].split(" ")
                
                # check phoneme in phones.txt
                try:
                    for phone in ipa_list:
                        _ = phone_dct[phone]
                    
                    _c = " ".join([user_dct[phrase]["DisplayAs"], str(fake_weight), user_dct[phrase]["IPA"]])
                    ipa_lex.append(_c.split())

                except:
                    print("this line {ipa_str} in {phrase}:IPA is illagel".format(ipa_str=user_dct[phrase]["IPA"], phrase=phrase))
                    continue
        
        if ipa_lex != []:
            return list2fst(make_context_fst(ipa_lex, weight=False), self.phone_table, self.word_table())
        else:
            return list2fst(None, self.phone_table, self.word_table())
