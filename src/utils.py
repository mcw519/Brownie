# Copyright 2020 (author: Meng Wu)

import io
import math

class DataIO():
    def __init__(self, encode="utf-8", split_space=" "):
        self.encode = encode
        self.split_space = split_space
        
    def read_word_table(self, x, is_reversed=False):
        dct = {}
        with io.open(x, "r", encoding=self.encode) as f:
            for line in f.readlines():
                key, idx = line.strip().split(self.split_space)
                if is_reversed:
                    dct.update({idx: key})
                else:
                    dct.update({key: idx})
        
        return dct
    
    def read_file_to_dict(self, x):
        dct = {}
        with io.open(x, "r", encoding=self.encode) as f:
            for line in f.readlines():
                key = line.strip().split(self.split_space)[0]
                content = " ".join(line.strip().split(self.split_space)[1:])
                dct.update({key: content})
            
        return dct

    def read_file_to_list(self, x):
        with io.open(x, 'r', encoding=self.encode) as f:
            result=[ i.strip().split(self.split_space) for i in f.readlines() ]
            
        return result
    
    def write_word_tb(self, dct, file_path):
        f = io.open(file_path, "w", encoding="utf-8")
        for wd in dct.keys():
            idx = dct[wd]
            f.write("{} {}\n".format(wd, idx))
    
        f.close()


def lex_add_disambig(x):
    """
        x: lexicon string path.
    """
    lex_dct = {}
    with io.open(x, "r", encoding="utf8") as f:
        for line in f.readlines():
            wd = line.strip().split()[0]
            phseq = " ".join(line.strip().split()[1:])

            try:
                lex_dct[phseq]
                lex_dct[phseq].append(wd)
            except:
                lex_dct[phseq] = [wd]

    o_list = []
    ndis = 0
    for key in lex_dct.keys():
        if len(lex_dct[key]) == 1:
            o_list.append(lex_dct[key][0] + " " + key)
        else:
            dis = 1
            for wd in lex_dct[key]:
                o_list.append(wd + " " + key + " #" + str(dis))
                dis += 1
        
        if len(lex_dct[key]) > ndis:
            ndis = len(lex_dct[key])

    return o_list, ndis
    

def update_wd_table(wd_table, oov_list):
    """
        Input:
            wd_table: dict
            oov_list: list
            write: string path
        Return:
            new_wd_table: dict
    """
    if isinstance(oov_list, str):
        raise TypeError("need a list")

    for i in oov_list:
        try:
            # avoid repeatedly update inside class method
            wd_table[i]
            continue

        except KeyError:
            wd_table.update({i: str(len(wd_table.keys()))})

    return wd_table


def make_context_fst(x, weight=True):
    """
    read a Kaldi lexicon format list.
        <word1> <weight> <sub-word1> <sub-word2> <...>
        example:
            ABABA 1.0 ABABA
            ABACHA 1.0 ABACHA
            每日一物 100 每 日 一 物
            每日一物 100 每日 一物
    Returns:
        List with FST format.
    """
    C = x
    C_fst = []
    state = int(0)
    if weight:
        for i in range(len(C)):
            if len(C[i]) == 3:
                logprob = '%.10f' % (-math.log(float(C[i][1])))
                C_fst.append(['0', '0', C[i][2], C[i][0], logprob])
            else:
                logprob = '%.10f' % (-math.log(float(C[i][1])))
                for j in range(len(C[i]) - 2):
                    if j == 0:
                        C_fst.append(['0', '%s' %  (state + 1), C[i][j+2], C[i][0], logprob])
                        state = state + 1
                    elif j == len(C[i]) - 3:
                        C_fst.append(['%s' % state, '0', C[i][j+2], '<eps>'])
                    else:
                        C_fst.append(['%s' % state, '%s' % (state + 1), C[i][j+2], '<eps>'])
                        state = state + 1
        C_fst.append(['0','0']) # add end
    
    else:
        for i in range(len(C)):
            if len(C[i]) == 3:
                C_fst.append(['0', '0', C[i][2], C[i][0]])
            else:
                for j in range(len(C[i]) - 2):
                    if j == 0:
                        C_fst.append(['0', '%s' %  (state + 1), C[i][j+2], C[i][0]])
                        state = state + 1
                    elif j == len(C[i]) - 3:
                        C_fst.append(['%s' % state, '0', C[i][j+2], '<eps>'])
                    else:
                        C_fst.append(['%s' % state, '%s' % (state + 1), C[i][j+2], '<eps>'])
                        state = state + 1
        C_fst.append(['0','0']) # add end

    return C_fst


def sym2int(x, syms_table):
    """
        convert string to int sequence
        Input:
            x: string
            syms_table: dict
    """

    x = x.strip().split()
    result = []
    
    try:
        for _, i in enumerate(x):
            x_int = str(syms_table[i])
            result.append(x_int)
    
        return " ".join(result)
    
    except:
        raise KeyError("some words in string not in the provided symbol table")


def int2sym(x, syms_table):
    """
        convert int sequence to string
        Input:
            x: string
            syms_table: dict
    """
    syms_table = {v: k for k, v in syms_table.items()}

    x = x.strip().split()
    result = []
    
    try:
        for _, i in enumerate(x):
            x_sym = str(syms_table[i])
            result.append(x_sym)
    
        return " ".join(result)
    
    except:
        raise KeyError("some words in string not in the provided symbol table")
