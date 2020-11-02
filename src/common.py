# Copyright 2020 (author: Meng Wu)

import pynini

def list2fst(x, in_syms, out_syms):
    """
        Input:
            x is like:
                [['0', '1', '世界', '世博會', '0.1053605157'], ['1', '0', '博覽會', '<eps>'],
                ['0', '2', '一個', '一個巨星的誕生', '0.1053605157'], ['2', '3', '巨星', '<eps>'],
                ['3', '4', '的', '<eps>'], ['4', '0', '誕生', '<eps>']]
            in_syms, out_syms is symbols table (dict)
        Return:
            Fst
    """
    if x is not None:
        fst = pynini.Fst()
        fst.add_state()
        fst.set_start(0)
        for i in x:
            if len(i) == 5:
                state_in, state_out, arc_in, arc_out, arc_weight = i
                state_in = int(state_in)
                state_out = int(state_out)
                arc_in = int(in_syms[arc_in])
                arc_out = int(out_syms[arc_out])
                arc_weight = pynini.Weight("tropical", float(arc_weight))
                fst.add_state()
                fst.add_arc(state_in, pynini.Arc(arc_in, arc_out, arc_weight, state_out))
            
            elif len(i) == 4:
                state_in, state_out, arc_in, arc_out = i
                state_in = int(state_in)
                state_out = int(state_out)
                arc_in = int(in_syms[arc_in])
                arc_out = int(out_syms[arc_out])
                arc_weight = pynini.Weight("tropical", 0)
                fst.add_state()
                fst.add_arc(state_in, pynini.Arc(arc_in, arc_out, arc_weight, state_out))
            
            else:
                fst.set_final(0)
        
        return fst.optimize()
    
    else:

        raise(ValueError, "empty fst list")


def load_fst(x):
    return pynini.Fst.read(x)


def read_string_as_fst(x):
    x_list = x.split()
    fst = pynini.Fst()
    fst.add_state()

    for idx, value in enumerate(x_list):
        value = int(value)
        fst.add_state()
        fst.add_arc(idx, pynini.Arc(value, value, pynini.Weight("tropical", 0), idx + 1))
    
    fst.set_start(0)
    fst.set_final(idx + 1)

    return fst


def compose(fst1, fst2, direction="right", project=None):
    """
        Args:
            direction: (string)
                right: fst1 o fst2
                left: fst2 o fst1
    """
    if direction == "right":
        fst = pynini.compose(fst1, fst2)
    elif direction == "left":
        fst = pynini.compose(fst2, fst1)
    else:
        raise ValueError("direction is only right or left")

    if fst.print() != "":
        if project is not None:
            fst.project(project)
            return fst.optimize()
        else:
            return fst.optimize()
    else:
        if direction == "right":
            return fst1
        else:
            return fst2


def union(*args):
    fst = pynini.Fst()
    for arg in args:
        fst.union(arg)
    
    return fst


def get_result(x, *args):
    for arg in args:
        x = pynini.compose(x, arg)
    
    x.project("output")
    x.optimize()
    x = pynini.shortestpath(x)

    return pynini.topsort(x)


def fst_to_linear_sequence(x, syms=None):
    """
        convert a fst into a linear sequence
    """
    best_path = pynini.topsort(pynini.shortestpath(x))
    seq = []
    for line in best_path.print().split("\n"):
        try:
            if syms is not None:
                try:
                    temp = syms[line.strip().split()[3]]
                except:
                    pass
            else:
                temp = line.strip().split()[3]
            seq.append(temp)
        except:
            continue
    

    return " ".join(seq)
